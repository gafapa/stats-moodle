"""
Recolector de datos de Moodle.
Obtiene y estructura todos los datos de un curso para su análisis.
"""
import time
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from .moodle_client import MoodleClient


class DataCollector:
    """
    Orquesta la recolección de todos los datos de un curso desde Moodle.
    Reporta progreso mediante callbacks para actualizar la UI.
    """

    def __init__(self, client: MoodleClient):
        self.client = client
        self._progress_callback: Optional[Callable[[str, int], None]] = None

    def set_progress_callback(self, callback: Callable[[str, int], None]):
        """Registra callback para reportar progreso: callback(mensaje, porcentaje)."""
        self._progress_callback = callback

    def _progress(self, msg: str, pct: int):
        if self._progress_callback:
            self._progress_callback(msg, pct)

    # ------------------------------------------------------------------
    # Recolección principal
    # ------------------------------------------------------------------

    def collect_course_data(self, course_id: int, course_info: Optional[Dict] = None) -> Dict:
        """
        Recolecta todos los datos del curso y los devuelve como dict estructurado.
        Este método puede tardar varios segundos dependiendo del tamaño del curso.
        """
        data: Dict[str, Any] = {
            "course": {},
            "students": [],
            "assignments": [],
            "quizzes": [],
            "forums": [],
            "contents": [],
            "logs_available": False,
            "collected_at": datetime.now().isoformat(),
        }

        # 1. Información del curso
        self._progress("Obteniendo información del curso...", 5)
        if course_info is None:
            courses = self.client.get_courses()
            course_info = next((c for c in courses if c["id"] == course_id), {"id": course_id})
        data["course"] = dict(course_info)

        # 2. Estructura del curso (secciones/actividades)
        self._progress("Obteniendo estructura del curso...", 10)
        data["contents"] = self.client.get_course_contents(course_id)

        # 3. Tareas
        self._progress("Obteniendo tareas...", 15)
        assignments = self.client.get_assignments(course_id)
        data["assignments"] = assignments

        # 4. Cuestionarios
        self._progress("Obteniendo cuestionarios...", 20)
        data["quizzes"] = self.client.get_quizzes(course_id)

        # 5. Foros
        self._progress("Obteniendo foros...", 25)
        data["forums"] = self.client.get_forums(course_id)

        # 6. Entregas de tareas
        self._progress("Obteniendo entregas de tareas...", 30)
        submissions_by_assign: Dict[int, List[Dict]] = {}
        for assign in assignments:
            aid = assign.get("id")
            if aid:
                submissions_by_assign[aid] = self.client.get_submissions(aid)
        data["submissions_by_assign"] = submissions_by_assign

        # 7. Intentos de cuestionarios
        self._progress("Obteniendo intentos de cuestionarios...", 38)
        attempts_by_quiz: Dict[int, List[Dict]] = {}
        for quiz in data["quizzes"]:
            qid = quiz.get("id")
            if qid:
                attempts_by_quiz[qid] = self.client.get_user_attempts(qid)
        data["attempts_by_quiz"] = attempts_by_quiz

        # 8. Posts de foros
        self._progress("Obteniendo participación en foros...", 45)
        posts_by_user = self._collect_forum_posts(data["forums"])
        data["posts_by_user"] = posts_by_user

        # 9. Usuarios matriculados
        self._progress("Obteniendo usuarios matriculados...", 50)
        enrolled = self.client.get_enrolled_users(course_id)
        enrolled = self._enrich_users_with_profiles(course_id, enrolled)
        # Filtrar solo alumnos (role: student / editingteacher / teacher)
        students = [
            u for u in enrolled
            if self._is_student(u)
        ]
        data["students_raw"] = students

        # 10. Logs de actividad (opcionales)
        self._progress("Intentando obtener logs de actividad...", 55)
        logs = self.client.get_user_logs(course_id)
        if logs:
            data["logs_available"] = True
            data["logs"] = logs
        else:
            data["logs_available"] = False
            data["logs"] = []

        # 11. Datos por alumno
        total_students = len(students)
        student_data_list = []
        for idx, student in enumerate(students):
            uid = student.get("id")
            name = student.get("fullname", f"Usuario {uid}")
            pct = 58 + int((idx / max(total_students, 1)) * 35)
            self._progress(f"Analizando alumno {idx+1}/{total_students}: {name}...", pct)
            student_data = self._collect_student_data(
                student,
                course_id,
                data["assignments"],
                data["quizzes"],
                submissions_by_assign,
                attempts_by_quiz,
                posts_by_user,
                data["contents"],
                data.get("logs", []),
            )
            student_data_list.append(student_data)

        data["students"] = student_data_list
        self._progress("Recolección completada.", 100)
        return data

    # ------------------------------------------------------------------
    # Datos por alumno
    # ------------------------------------------------------------------

    def _collect_student_data(
        self,
        user: Dict,
        course_id: int,
        assignments: List[Dict],
        quizzes: List[Dict],
        submissions_by_assign: Dict,
        attempts_by_quiz: Dict,
        posts_by_user: Dict,
        contents: List[Dict],
        logs: List[Dict],
    ) -> Dict:
        uid = user.get("id")

        # Calificaciones
        grade_data = self.client.get_grade_items_for_user(course_id, uid)
        grades = self._parse_grade_items(grade_data)

        # Completitud de actividades
        completion_data = self.client.get_activities_completion(course_id, uid)
        completion = self._parse_completion(completion_data)

        # Entregas por alumno
        student_submissions = self._filter_submissions(submissions_by_assign, uid)

        # Intentos de cuestionario por alumno
        student_attempts = self._filter_attempts(attempts_by_quiz, uid)

        # Posts en foros
        user_posts = posts_by_user.get(uid, [])

        # Logs del alumno (si disponibles)
        user_logs = [l for l in logs if l.get("userid") == uid]

        return {
            "id": uid,
            "fullname": user.get("fullname", ""),
            "email": user.get("email", ""),
            "lastaccess": user.get("lastaccess", 0),
            "firstaccess": user.get("firstaccess", 0),
            "enrolled": user.get("lastcourseaccess", 0),
            "country": user.get("country", ""),
            "profileimageurl": user.get("profileimageurl", ""),
            # Datos recogidos
            "grades": grades,
            "completion": completion,
            "submissions": student_submissions,
            "quiz_attempts": student_attempts,
            "forum_posts": user_posts,
            "logs": user_logs,
        }

    # ------------------------------------------------------------------
    # Parsers de respuestas API
    # ------------------------------------------------------------------

    def _parse_grade_items(self, data: Dict) -> Dict:
        """Extrae información de calificaciones de la respuesta de gradereport_user."""
        if not data or not isinstance(data, dict):
            return {"items": [], "final_grade": None, "final_grade_pct": None}

        items = []
        final_grade = None
        final_grade_pct = None
        course_total_max = None

        user_grades = data.get("usergrades", [])
        if user_grades:
            grade_report = user_grades[0]
            grade_items_raw = grade_report.get("gradeitems", [])
            for item in grade_items_raw:
                item_type = item.get("itemtype", "")
                # El item de tipo "course" es la nota total del curso
                if item_type == "course":
                    raw = item.get("graderaw")
                    max_grade = item.get("grademax", 10)
                    if raw is not None:
                        try:
                            final_grade = float(raw)
                            if max_grade and float(max_grade) > 0:
                                final_grade_pct = (final_grade / float(max_grade)) * 100
                                course_total_max = float(max_grade)
                        except (ValueError, TypeError):
                            pass
                else:
                    raw = item.get("graderaw")
                    max_g = item.get("grademax", 10)
                    min_g = item.get("grademin", 0)
                    try:
                        grade_val = float(raw) if raw is not None else None
                        max_val = float(max_g) if max_g is not None else 10.0
                        pct = (grade_val / max_val * 100) if (grade_val is not None and max_val > 0) else None
                    except (ValueError, TypeError):
                        grade_val = None
                        pct = None

                    items.append({
                        "id": item.get("id"),
                        "name": item.get("itemname") or item.get("categoryname", "Sin nombre"),
                        "type": item_type,
                        "modname": item.get("itemmodule", ""),
                        "grade": grade_val,
                        "grade_pct": pct,
                        "max_grade": float(max_g) if max_g else 10.0,
                        "min_grade": float(min_g) if min_g else 0.0,
                        "gradedate": item.get("gradedategraded"),
                        "feedback": item.get("feedback", ""),
                    })

        return {
            "items": items,
            "final_grade": final_grade,
            "final_grade_pct": final_grade_pct,
            "course_total_max": course_total_max,
        }

    def _parse_completion(self, data: Dict) -> Dict:
        """Extrae estado de completitud de actividades."""
        if not data or not isinstance(data, dict):
            return {"statuses": [], "completed": 0, "total": 0}

        statuses = data.get("statuses", [])
        completed = sum(1 for s in statuses if s.get("state") in (1, 2))
        return {
            "statuses": statuses,
            "completed": completed,
            "total": len(statuses),
        }

    def _filter_submissions(self, submissions_by_assign: Dict, user_id: int) -> List[Dict]:
        """Filtra entregas de un alumno concreto."""
        result = []
        for assign_id, subs in submissions_by_assign.items():
            for sub in subs:
                if sub.get("userid") == user_id:
                    result.append({**sub, "assignid": assign_id})
        return result

    def _filter_attempts(self, attempts_by_quiz: Dict, user_id: int) -> List[Dict]:
        """Filtra intentos de cuestionario de un alumno concreto."""
        result = []
        for quiz_id, attempts in attempts_by_quiz.items():
            for att in attempts:
                if att.get("userid") == user_id:
                    result.append({**att, "quizid": quiz_id})
        return result

    def _collect_forum_posts(self, forums: List[Dict]) -> Dict[int, List[Dict]]:
        """Recopila posts de foros, indexados por user_id."""
        posts_by_user: Dict[int, List[Dict]] = {}
        per_page = 100
        for forum in forums:
            fid = forum.get("id")
            if not fid:
                continue
            seen_discussions = set()
            page = 0
            while True:
                discussions = self.client.get_forum_discussions(fid, page=page, per_page=per_page)
                if not discussions:
                    break
                new_ids = 0
                for disc in discussions:
                    disc_id = disc.get("id") or disc.get("discussion")
                    if not disc_id or disc_id in seen_discussions:
                        continue
                    seen_discussions.add(disc_id)
                    new_ids += 1
                    posts = self.client.get_discussion_posts(disc_id)
                    for post in posts:
                        uid = post.get("userid")
                        if uid:
                            posts_by_user.setdefault(uid, []).append({
                                **post,
                                "forumid": fid,
                                "discussionid": disc_id,
                            })
                if new_ids == 0:
                    break
                page += 1
        return posts_by_user

    def _enrich_users_with_profiles(self, course_id: int, users: List[Dict]) -> List[Dict]:
        """Completa roles y otros metadatos cuando la matrícula no los incluye."""
        missing_ids = [u.get("id") for u in users if u.get("id") and not u.get("roles")]
        if not missing_ids:
            return users

        profiles_by_id: Dict[int, Dict] = {}
        batch_size = 50
        for i in range(0, len(missing_ids), batch_size):
            batch_ids = missing_ids[i:i + batch_size]
            profiles = self.client.get_course_user_profiles(course_id, batch_ids)
            if not isinstance(profiles, list):
                continue
            for profile in profiles:
                uid = profile.get("id")
                if uid:
                    profiles_by_id[uid] = profile

        enriched_users = []
        for user in users:
            profile = profiles_by_id.get(user.get("id"))
            if not profile:
                enriched_users.append(user)
                continue
            merged = dict(user)
            for key in ("roles", "fullname", "email", "country", "profileimageurl"):
                value = profile.get(key)
                if value not in (None, "", []):
                    merged[key] = value
            enriched_users.append(merged)
        return enriched_users

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    @staticmethod
    def _is_student(user: Dict) -> bool:
        """Determina si un usuario matriculado es alumno (no profesor/admin)."""
        roles = user.get("roles", [])
        if not roles:
            return False
        teacher_roles = {"editingteacher", "teacher", "manager", "coursecreator"}
        for role in roles:
            shortname = role.get("shortname", "").lower()
            if shortname in teacher_roles:
                return False
        return True

    @staticmethod
    def count_activities_in_contents(contents: List[Dict]) -> Dict[str, int]:
        """Cuenta el número total de cada tipo de actividad en el curso."""
        counts: Dict[str, int] = {}
        for section in contents:
            for module in section.get("modules", []):
                mtype = module.get("modname", "unknown")
                counts[mtype] = counts.get(mtype, 0) + 1
        return counts

    @staticmethod
    def get_activity_timestamps(contents: List[Dict]) -> List[Dict]:
        """Extrae la lista de módulos con sus timestamps para línea de tiempo."""
        modules = []
        for section in contents:
            for mod in section.get("modules", []):
                modules.append({
                    "id": mod.get("id"),
                    "name": mod.get("name", ""),
                    "modname": mod.get("modname", ""),
                    "visible": mod.get("visible", 1),
                    "availablefrom": mod.get("availablefrom", 0),
                    "availableuntil": mod.get("availableuntil", 0),
                })
        return modules

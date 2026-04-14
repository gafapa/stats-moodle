"""
Cliente para la API REST de Moodle.
Solo usa endpoints de consulta (GET/POST de lectura), nunca de modificación.
"""
import requests
import json
from typing import Optional, List, Dict, Any


class MoodleAPIError(Exception):
    pass


class MoodleClient:
    """
    Cliente para la API REST de Moodle.
    Autenticación mediante token o usuario/contraseña.
    Solo llamadas de lectura.
    """

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MoodleAnalyzer/1.0"})
        # Info del sitio y usuario autenticado
        self.site_name = ""
        self.user_id = None
        self.user_fullname = ""
        self._test_connection()

    # ------------------------------------------------------------------
    # Autenticación
    # ------------------------------------------------------------------

    @classmethod
    def from_credentials(
        cls,
        base_url: str,
        username: str,
        password: str,
        service: str = "moodle_mobile_app",
    ) -> "MoodleClient":
        """Crea el cliente usando usuario y contraseña (obtiene token automáticamente)."""
        token_url = f"{base_url.rstrip('/')}/login/token.php"
        try:
            resp = requests.post(
                token_url,
                data={"username": username, "password": password, "service": service},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                raise MoodleAPIError(
                    f"Login fallido: {data.get('error', 'Credenciales inválidas')}"
                )
            token = data.get("token")
            if not token:
                raise MoodleAPIError("No se recibió token del servidor")
            return cls(base_url, token)
        except requests.exceptions.ConnectionError:
            raise MoodleAPIError(f"No se puede conectar a: {base_url}")
        except requests.exceptions.Timeout:
            raise MoodleAPIError("Tiempo de espera agotado al conectar")
        except requests.exceptions.RequestException as e:
            raise MoodleAPIError(f"Error de conexión: {e}")

    # ------------------------------------------------------------------
    # Llamada base a la API
    # ------------------------------------------------------------------

    def _api_call(self, function: str, params: Optional[Dict] = None) -> Any:
        """Realiza una llamada a la API REST de Moodle."""
        url = f"{self.base_url}/webservice/rest/server.php"
        payload = {
            "wstoken": self.token,
            "wsfunction": function,
            "moodlewsrestformat": "json",
        }
        if params:
            payload.update(self._flatten(params))

        try:
            resp = self.session.post(url, data=payload, timeout=60)
            resp.raise_for_status()
            result = resp.json()
            if isinstance(result, dict) and "exception" in result:
                msg = result.get("message", result.get("debuginfo", "Error desconocido"))
                raise MoodleAPIError(f"API [{function}]: {msg}")
            return result
        except requests.exceptions.ConnectionError:
            raise MoodleAPIError(f"Sin conexión al servidor: {self.base_url}")
        except requests.exceptions.Timeout:
            raise MoodleAPIError(f"Tiempo de espera agotado en [{function}]")
        except requests.exceptions.RequestException as e:
            raise MoodleAPIError(f"Error HTTP: {e}")
        except json.JSONDecodeError:
            raise MoodleAPIError("Respuesta inválida del servidor (no es JSON)")

    def _api_call_safe(self, function: str, params: Optional[Dict] = None, default=None):
        """Llama a la API y devuelve `default` si falla (en lugar de lanzar excepción)."""
        try:
            return self._api_call(function, params)
        except MoodleAPIError:
            return default

    @staticmethod
    def _flatten(params: Dict, prefix: str = "") -> Dict:
        """Convierte dict/listas anidadas al formato de parámetros de Moodle REST."""
        result = {}
        for key, value in params.items():
            full_key = f"{prefix}[{key}]" if prefix else key
            if isinstance(value, dict):
                result.update(MoodleClient._flatten(value, full_key))
            elif isinstance(value, list):
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        result.update(MoodleClient._flatten(item, f"{full_key}[{i}]"))
                    else:
                        result[f"{full_key}[{i}]"] = item
            else:
                result[full_key] = value
        return result

    # ------------------------------------------------------------------
    # Conexión y sitio
    # ------------------------------------------------------------------

    def _test_connection(self):
        info = self._api_call("core_webservice_get_site_info")
        self.site_name = info.get("sitename", "Moodle")
        self.user_id = info.get("userid")
        self.user_fullname = info.get("fullname", "")

    def get_site_info(self) -> Dict:
        return self._api_call("core_webservice_get_site_info")

    # ------------------------------------------------------------------
    # Cursos
    # ------------------------------------------------------------------

    def get_my_courses(self) -> List[Dict]:
        """Cursos accesibles para el usuario autenticado.

        Prueba tres endpoints en orden, devolviendo el primero que funcione:
          1. core_enrol_get_my_courses       — matrícula genérica (alumno/docente)
          2. core_enrol_get_users_courses    — cursos donde el usuario tiene ROL
                                              (cubre profesores y creadores de curso)
          3. core_course_get_courses         — todos los cursos (requiere admin)
        """
        # Intento 1: matriculados en sentido amplio
        result = self._api_call_safe(
            "core_enrol_get_my_courses",
            {"returnusercount": 1},
            default=[],
        )
        if isinstance(result, list):
            courses = [c for c in result if c.get("id", 0) > 1]
            if courses:
                return courses

        # Intento 2: cursos por userid (funciona para profesores y creadores)
        if self.user_id:
            result = self._api_call_safe(
                "core_enrol_get_users_courses",
                {"userid": self.user_id},
                default=[],
            )
            if isinstance(result, list):
                courses = [c for c in result if c.get("id", 0) > 1]
                if courses:
                    return courses

        # Intento 3: todos los cursos del sitio (admin)
        return self.get_all_courses()

    def get_all_courses(self) -> List[Dict]:
        """Todos los cursos (requiere permisos de administrador o gestor)."""
        result = self._api_call_safe("core_course_get_courses", default=[])
        if isinstance(result, list):
            return [c for c in result if c.get("id", 0) > 1]
        return []

    def get_enrollment_count(self, course_id: int) -> int:
        """Número de usuarios matriculados en un curso."""
        users = self._api_call_safe(
            "core_enrol_get_enrolled_users",
            {"courseid": course_id},
            default=[],
        )
        return len(users) if isinstance(users, list) else 0

    def get_courses(self) -> List[Dict]:
        """
        Devuelve los cursos disponibles.
        get_my_courses() ya incluye enrolledusercount (returnusercount=1).
        Para get_all_courses() el enriquecimiento se hace de forma progresiva
        en la UI para no bloquear la carga inicial.
        """
        courses = self.get_my_courses()
        if not courses:
            courses = self.get_all_courses()
        return courses

    def get_course_contents(self, course_id: int) -> List[Dict]:
        """Estructura del curso: secciones y actividades."""
        return self._api_call_safe(
            "core_course_get_contents", {"courseid": course_id}, default=[]
        )

    # ------------------------------------------------------------------
    # Usuarios / Matriculaciones
    # ------------------------------------------------------------------

    def get_enrolled_users(self, course_id: int) -> List[Dict]:
        """Usuarios matriculados en un curso."""
        return self._api_call_safe(
            "core_enrol_get_enrolled_users", {"courseid": course_id}, default=[]
        )

    def get_course_user_profiles(self, course_id: int, user_ids: List[int]) -> List[Dict]:
        """Perfiles completos de usuarios en un curso."""
        params: Dict[str, Any] = {"courseid": course_id}
        for i, uid in enumerate(user_ids):
            params[f"userids[{i}]"] = uid
        return self._api_call_safe("core_user_get_course_user_profiles", params, default=[])

    # ------------------------------------------------------------------
    # Calificaciones
    # ------------------------------------------------------------------

    def get_grade_items_for_user(self, course_id: int, user_id: int) -> Dict:
        """Items de calificación para un usuario en un curso."""
        return self._api_call_safe(
            "gradereport_user_get_grade_items",
            {"courseid": course_id, "userid": user_id},
            default={},
        )

    def get_grades(self, course_id: int, user_ids: List[int]) -> Dict:
        """Calificaciones para múltiples usuarios (API simplificada)."""
        params: Dict[str, Any] = {"courseid": course_id}
        for i, uid in enumerate(user_ids):
            params[f"userids[{i}]"] = uid
        return self._api_call_safe("core_grades_get_grades", params, default={})

    def get_gradebook_overview(self, course_id: int) -> List[Dict]:
        """Vista general del libro de calificaciones."""
        result = self._api_call_safe(
            "gradereport_overview_get_course_grades",
            {"userid": self.user_id},
            default={},
        )
        return result.get("grades", []) if isinstance(result, dict) else []

    # ------------------------------------------------------------------
    # Completitud de actividades
    # ------------------------------------------------------------------

    def get_activities_completion(self, course_id: int, user_id: int) -> Dict:
        """Estado de completitud de actividades para un usuario."""
        return self._api_call_safe(
            "core_completion_get_activities_completion_status",
            {"courseid": course_id, "userid": user_id},
            default={},
        )

    def get_course_completion_status(self, course_id: int, user_id: int) -> Dict:
        """Completitud global del curso para un usuario."""
        return self._api_call_safe(
            "core_completion_get_course_completion_status",
            {"courseid": course_id, "userid": user_id},
            default={},
        )

    # ------------------------------------------------------------------
    # Tareas (Assignments)
    # ------------------------------------------------------------------

    def get_assignments(self, course_id: int) -> List[Dict]:
        """Tareas del curso."""
        result = self._api_call_safe(
            "mod_assign_get_assignments",
            {"courseids[0]": course_id},
            default={"courses": []},
        )
        courses = result.get("courses", []) if isinstance(result, dict) else []
        return courses[0].get("assignments", []) if courses else []

    def get_submissions(self, assign_id: int) -> List[Dict]:
        """Entregas de una tarea."""
        result = self._api_call_safe(
            "mod_assign_get_submissions",
            {"assignmentids[0]": assign_id},
            default={"assignments": []},
        )
        assignments = result.get("assignments", []) if isinstance(result, dict) else []
        return assignments[0].get("submissions", []) if assignments else []

    def get_submission_statuses(self, assign_id: int) -> List[Dict]:
        """Estado de entrega por usuario para una tarea."""
        result = self._api_call_safe(
            "mod_assign_get_submission_status",
            {"assignid": assign_id},
            default={},
        )
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Cuestionarios (Quizzes)
    # ------------------------------------------------------------------

    def get_quizzes(self, course_id: int) -> List[Dict]:
        """Cuestionarios del curso."""
        result = self._api_call_safe(
            "mod_quiz_get_quizzes_by_courses",
            {"courseids[0]": course_id},
            default={"quizzes": []},
        )
        return result.get("quizzes", []) if isinstance(result, dict) else []

    def get_user_attempts(self, quiz_id: int, user_id: int = 0) -> List[Dict]:
        """Intentos de un cuestionario. user_id=0 para todos."""
        params: Dict[str, Any] = {"quizid": quiz_id}
        if user_id:
            params["userid"] = user_id
        result = self._api_call_safe("mod_quiz_get_user_attempts", params, default={"attempts": []})
        return result.get("attempts", []) if isinstance(result, dict) else []

    def get_quiz_attempt_review(self, attempt_id: int) -> Dict:
        """Revisión de un intento de cuestionario."""
        return self._api_call_safe(
            "mod_quiz_get_attempt_review",
            {"attemptid": attempt_id},
            default={},
        )

    # ------------------------------------------------------------------
    # Foros
    # ------------------------------------------------------------------

    def get_forums(self, course_id: int) -> List[Dict]:
        """Foros del curso."""
        return self._api_call_safe(
            "mod_forum_get_forums_by_courses",
            {"courseids[0]": course_id},
            default=[],
        )

    def get_forum_discussions(self, forum_id: int, page: int = 0, per_page: int = 100) -> List[Dict]:
        """Discusiones de un foro."""
        result = self._api_call_safe(
            "mod_forum_get_forum_discussions",
            {"forumid": forum_id, "page": page, "perpage": per_page},
            default={"discussions": []},
        )
        if isinstance(result, dict):
            return result.get("discussions", [])
        if isinstance(result, list):
            return result
        return []

    def get_discussion_posts(self, discussion_id: int) -> List[Dict]:
        """Posts de una discusión de foro."""
        result = self._api_call_safe(
            "mod_forum_get_forum_discussion_posts",
            {"discussionid": discussion_id},
            default={"posts": []},
        )
        return result.get("posts", []) if isinstance(result, dict) else []

    # ------------------------------------------------------------------
    # Logs de actividad
    # ------------------------------------------------------------------

    def get_user_logs(
        self,
        course_id: int,
        user_id: int = 0,
        date: int = 0,
        modname: str = "",
        action: str = "",
    ) -> List[Dict]:
        """
        Logs de actividad (requiere permisos de admin/gestor en muchas instalaciones).
        Devuelve lista vacía si no hay permisos.
        """
        params: Dict[str, Any] = {"courseid": course_id, "edulevel": -1}
        if user_id:
            params["userid"] = user_id
        if date:
            params["date"] = date
        if modname:
            params["modname"] = modname
        if action:
            params["action"] = action
        result = self._api_call_safe("report_log_get_log", params, default={"logs": []})
        if isinstance(result, dict):
            return result.get("logs", [])
        if isinstance(result, list):
            return result
        return []

    def get_insights(self, course_id: int) -> List[Dict]:
        """Predicciones/insights de Moodle (si está habilitado analytics)."""
        result = self._api_call_safe(
            "tool_analytics_potential_contexts",
            {"modelid": 1},
            default=[],
        )
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Recursos y módulos
    # ------------------------------------------------------------------

    def get_course_module(self, cm_id: int) -> Dict:
        """Información de un módulo de curso."""
        return self._api_call_safe(
            "core_course_get_course_module",
            {"cmid": cm_id},
            default={},
        )

    def get_pages(self, course_id: int) -> List[Dict]:
        """Páginas de contenido del curso."""
        result = self._api_call_safe(
            "mod_page_get_pages_by_courses",
            {"courseids[0]": course_id},
            default={"pages": []},
        )
        return result.get("pages", []) if isinstance(result, dict) else []

    def get_resources(self, course_id: int) -> List[Dict]:
        """Recursos (ficheros) del curso."""
        result = self._api_call_safe(
            "mod_resource_get_resources_by_courses",
            {"courseids[0]": course_id},
            default={"resources": []},
        )
        return result.get("resources", []) if isinstance(result, dict) else []

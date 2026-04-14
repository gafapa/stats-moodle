import time
import unittest

from src.analyzer import CourseAnalyzer
from src.data_collector import DataCollector
from src.ui_dashboard import CourseSelectionPanel


class FakeCollectorClient:
    def __init__(self):
        self._forum_pages = {
            (10, 0): [{"id": 1}, {"id": 2}],
            (10, 1): [{"id": 3}],
            (10, 2): [],
        }

    def get_courses(self):
        return [{"id": 10, "fullname": "Mi curso"}]

    def get_course_contents(self, course_id):
        return []

    def get_assignments(self, course_id):
        return []

    def get_quizzes(self, course_id):
        return []

    def get_forums(self, course_id):
        return [{"id": 10}]

    def get_submissions(self, assign_id):
        return []

    def get_user_attempts(self, quiz_id):
        return []

    def get_forum_discussions(self, forum_id, page=0, per_page=100):
        return self._forum_pages.get((forum_id, page), [])

    def get_discussion_posts(self, discussion_id):
        return [{"userid": discussion_id, "id": discussion_id * 100}]

    def get_enrolled_users(self, course_id):
        return [
            {"id": 1, "fullname": "Docente sin roles"},
            {"id": 2, "fullname": "Alumno sin roles"},
        ]

    def get_course_user_profiles(self, course_id, user_ids):
        profiles = {
            1: {"id": 1, "roles": [{"shortname": "teacher"}]},
            2: {"id": 2, "roles": [{"shortname": "student"}]},
        }
        return [profiles[uid] for uid in user_ids if uid in profiles]

    def get_user_logs(self, course_id):
        return []

    def get_grade_items_for_user(self, course_id, user_id):
        return {}

    def get_activities_completion(self, course_id, user_id):
        return {}


class FakeCourseOnlyClient(FakeCollectorClient):
    def get_forums(self, course_id):
        return []

    def get_enrolled_users(self, course_id):
        return []

    def get_course_user_profiles(self, course_id, user_ids):
        return []


class RegressionTests(unittest.TestCase):
    def test_course_selection_uses_translated_all_courses_label(self):
        panel = CourseSelectionPanel.__new__(CourseSelectionPanel)
        panel._course_mode = "🌐  All courses"
        panel._mode_all_label = "🌐  All courses"

        self.assertTrue(panel._use_all_courses())

    def test_course_selection_rejects_stale_load_results(self):
        panel = CourseSelectionPanel.__new__(CourseSelectionPanel)
        panel._load_request_id = 3

        self.assertTrue(panel._is_active_load(3))
        self.assertFalse(panel._is_active_load(2))

    def test_collect_course_data_preserves_selected_course_metadata(self):
        collector = DataCollector(FakeCourseOnlyClient())

        data = collector.collect_course_data(99, course_info={"id": 99, "fullname": "Curso global"})

        self.assertEqual(data["course"]["fullname"], "Curso global")

    def test_collect_forum_posts_paginates_all_discussions(self):
        collector = DataCollector(FakeCollectorClient())

        posts_by_user = collector._collect_forum_posts([{"id": 10}])

        self.assertEqual(sorted(posts_by_user.keys()), [1, 2, 3])

    def test_collect_course_data_enriches_roles_before_filtering_students(self):
        collector = DataCollector(FakeCollectorClient())

        data = collector.collect_course_data(10, course_info={"id": 10, "fullname": "Curso"})

        self.assertEqual([student["id"] for student in data["students_raw"]], [2])

    def test_optional_course_components_do_not_create_false_risk_factors(self):
        now = int(time.time())
        student = {
            "id": 7,
            "fullname": "Alumno",
            "lastaccess": now,
            "grades": {
                "items": [],
                "final_grade": 8.0,
                "final_grade_pct": 80.0,
                "course_total_max": 10.0,
            },
            "completion": {"statuses": [], "completed": 0, "total": 0},
            "submissions": [],
            "quiz_attempts": [],
            "forum_posts": [],
            "logs": [],
        }

        analysis = CourseAnalyzer().analyze({
            "course": {"id": 10, "fullname": "Curso"},
            "students": [student],
            "assignments": [],
            "quizzes": [],
            "forums": [],
            "logs_available": False,
        })
        result = analysis["students"][0]
        course_metrics = analysis["course_metrics"]

        self.assertEqual(result["risk_level"], "bajo")
        self.assertNotIn("Solo ha entregado el 0% de las tareas", result["risk_factors"])
        self.assertNotIn("Solo ha completado el 0% de las actividades", result["risk_factors"])
        self.assertNotIn("Sin participación en foros", result["risk_factors"])
        self.assertFalse(course_metrics["has_assignments"])
        self.assertFalse(course_metrics["has_quizzes"])
        self.assertFalse(course_metrics["has_forums"])
        self.assertIsNone(course_metrics["no_submissions"])
        self.assertIsNone(course_metrics["no_forum"])

    def test_custom_pass_threshold_changes_grade_risk_analysis(self):
        now = int(time.time())
        student = {
            "id": 8,
            "fullname": "Alumno umbral",
            "lastaccess": now,
            "grades": {
                "items": [],
                "final_grade": 5.5,
                "final_grade_pct": 55.0,
                "course_total_max": 10.0,
            },
            "completion": {"statuses": [], "completed": 0, "total": 0},
            "submissions": [],
            "quiz_attempts": [],
            "forum_posts": [],
            "logs": [],
        }
        course_data = {
            "course": {"id": 11, "fullname": "Curso"},
            "students": [student],
            "assignments": [],
            "quizzes": [],
            "forums": [],
            "logs_available": False,
        }

        analysis_default = CourseAnalyzer().analyze(course_data)
        analysis_custom = CourseAnalyzer(pass_threshold_pct=60.0).analyze(course_data)

        self.assertNotIn(
            "Calificación en riesgo de suspenso: 55%",
            analysis_default["students"][0]["risk_factors"],
        )
        self.assertIn(
            "Calificación en riesgo de suspenso: 55%",
            analysis_custom["students"][0]["risk_factors"],
        )
        self.assertEqual(analysis_custom["pass_threshold_pct"], 60.0)

    def test_high_grade_with_only_mild_signals_stays_low_risk(self):
        now = int(time.time())
        student = {
            "id": 9,
            "fullname": "Alumno sólido",
            "lastaccess": now - 8 * 86400,
            "grades": {
                "items": [],
                "final_grade": 8.0,
                "final_grade_pct": 80.0,
                "course_total_max": 10.0,
            },
            "completion": {"statuses": [], "completed": 0, "total": 0},
            "submissions": [],
            "quiz_attempts": [],
            "forum_posts": [],
            "logs": [],
        }
        analysis = CourseAnalyzer().analyze({
            "course": {"id": 12, "fullname": "Curso"},
            "students": [student],
            "assignments": [],
            "quizzes": [],
            "forums": [{"id": 1, "name": "Foro"}],
            "logs_available": False,
        })

        result = analysis["students"][0]

        self.assertEqual(result["risk_level"], "bajo")
        self.assertIn("No ha accedido en 8 días", result["risk_factors"])
        self.assertIn("Sin participación en foros", result["risk_factors"])


if __name__ == "__main__":
    unittest.main()

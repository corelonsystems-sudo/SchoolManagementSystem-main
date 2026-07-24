from jet.dashboard.dashboard import Dashboard, AppIndexDashboard
from jet.dashboard.modules import DashboardModule, Chart
from django.db.models import Count
from .models import Student, Course


class CustomIndexDashboard(Dashboard):
    columns = 3

    def init_with_context(self, context):
        # Add a bar chart for student distribution by course
        self.children.append(
            Chart(
                title="Students by Course",
                chart_type="bar",
                data_source=self.get_students_by_course(),
                x_field="course",
                y_field="count",
                x_label="Courses",
                y_label="Number of Students",
            )
        )

        # Add a pie chart for gender distribution
        self.children.append(
            Chart(
                title="Gender Distribution",
                chart_type="pie",
                data_source=self.get_gender_distribution(),
                label_field="gender",
                data_field="count",
            )
        )

    def get_students_by_course(self):
        return Student.objects.values(course=F("course__name")).annotate(count=Count("id"))

    def get_gender_distribution(self):
        return Student.objects.values("gender").annotate(count=Count("id"))

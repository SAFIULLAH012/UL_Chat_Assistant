"""
Models for the general/static side of the university system:
about-us, offices, faculties/departments/programs, fees, bus routes,
FAQs, and the chatbot's own content table.

NOTE: This app does NOT contain the timetable-generation models
(Teacher, Room, Course, LectureAllocation, TimeSlot, Timetable) from
Module 1 of the project blueprint. Those are a separate, bigger piece
(OR-Tools scheduling engine) and should live in their own app, e.g.
`scheduling`, built next.
"""
from django.db import models


# ---------------------------------------------------------------------------
# Singleton-ish university profile
# ---------------------------------------------------------------------------
class University(models.Model):
    name = models.CharField(max_length=255, default="University of Layyah")
    short_name = models.CharField(max_length=20, default="UL")
    website_domain = models.CharField(max_length=100, default="ul.edu.pk")
    admission_portal_url = models.URLField(blank=True)
    vision = models.TextField(blank=True)
    mission = models.TextField(blank=True)
    goals = models.JSONField(default=list, blank=True, help_text="List of goal strings")

    class Meta:
        verbose_name = "University Profile"
        verbose_name_plural = "University Profile"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # enforce a single row (singleton pattern), like a site-settings table
        self.pk = 1
        super().save(*args, **kwargs)


class Campus(models.Model):
    name = models.CharField(max_length=100, unique=True)
    address = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Campuses"

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Administration
# ---------------------------------------------------------------------------
class AdministrationRole(models.Model):
    """A leadership office: Vice Chancellor, Registrar, Treasurer, COE, etc."""
    role_id = models.SlugField(max_length=60, unique=True)
    name = models.CharField(max_length=150, help_text="Person currently holding the role")
    designation = models.CharField(max_length=150)
    responsibilities = models.TextField(blank=True)
    verified = models.BooleanField(default=True)

    class Meta:
        ordering = ["designation"]

    def __str__(self):
        return f"{self.designation} — {self.name}"


class RoleStaffMember(models.Model):
    """Support staff under an AdministrationRole (PA, clerical staff, etc.)."""
    role = models.ForeignKey(AdministrationRole, related_name="staff", on_delete=models.CASCADE)
    designation = models.CharField(max_length=150)
    name = models.CharField(max_length=150)

    def __str__(self):
        return f"{self.designation}: {self.name}"


# ---------------------------------------------------------------------------
# Offices / service departments (Library, Medical, Transport, Scholarships,
# QEC, Faculty Hostel, general Admission/Contact office).
# Kept as one flexible model with a JSON "details" bucket for the
# service-specific bits (facilities list, booking process, messages, etc.)
# so the CMS stays simple to extend without new migrations for every office.
# ---------------------------------------------------------------------------
class Office(models.Model):
    class OfficeType(models.TextChoices):
        LIBRARY = "library", "Library"
        MEDICAL = "medical", "Medical Center"
        TRANSPORT = "transport", "Transport Department"
        SCHOLARSHIPS = "scholarships", "Scholarships & Financial Aid"
        QEC = "qec", "Quality Enhancement Cell"
        FACULTY_HOSTEL = "faculty_hostel", "Faculty Hostel"
        ADMISSION = "admission", "Admission / Info Office"
        OTHER = "other", "Other"

    office_type = models.CharField(max_length=20, choices=OfficeType.choices, unique=True)
    display_name = models.CharField(max_length=150)
    description = models.TextField(blank=True, help_text="Short about-us style summary")
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True, help_text="Raw phone as given by the source")
    phone_local = models.CharField(max_length=20, blank=True)
    phone_intl = models.CharField(max_length=20, blank=True)
    hours = models.CharField(max_length=150, blank=True)
    contact_person = models.CharField(max_length=150, blank=True)
    verified = models.BooleanField(default=True)
    note = models.TextField(blank=True, help_text="Data-quality note, e.g. conflicting source info")
    details = models.JSONField(
        default=dict, blank=True,
        help_text="Service-specific extras: facilities list, booking_process, messages, etc."
    )

    class Meta:
        ordering = ["display_name"]

    def __str__(self):
        return self.display_name


# ---------------------------------------------------------------------------
# Academics: Faculty -> Department -> Program, plus fee groups
# ---------------------------------------------------------------------------
class Faculty(models.Model):
    faculty_id = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=200)

    class Meta:
        verbose_name_plural = "Faculties"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Department(models.Model):
    department_id = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=200)
    faculty = models.ForeignKey(Faculty, related_name="departments", on_delete=models.CASCADE)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class FeeGroup(models.Model):
    """A fee bracket shared by several programs, e.g. 'Computing Group'."""
    group_id = models.SlugField(max_length=60, unique=True)
    label = models.CharField(max_length=150)
    morning_semesters = models.JSONField(default=list, blank=True, help_text="List of per-semester fees (PKR)")
    morning_total = models.PositiveIntegerField(null=True, blank=True)
    afternoon_semesters = models.JSONField(default=list, blank=True)
    afternoon_total = models.PositiveIntegerField(null=True, blank=True)
    verified = models.BooleanField(default=True)

    def __str__(self):
        return self.label


class Program(models.Model):
    class ProgramType(models.TextChoices):
        UNDERGRADUATE = "Undergraduate", "Undergraduate"
        POST_ADP = "Post-ADP", "Post-ADP"
        DIPLOMA = "Diploma", "Diploma"
        PROFESSIONAL = "Professional Degree", "Professional Degree"

    class FeeStatus(models.TextChoices):
        CONFIRMED = "confirmed", "Confirmed"
        NEEDS_CONFIRMATION = "needs_confirmation", "Needs Confirmation"
        CONFLICT = "conflict", "Source Conflict"
        SUSPICIOUS = "suspicious", "Suspicious / Likely Wrong"

    program_id = models.SlugField(max_length=120, unique=True)
    name = models.CharField(max_length=200)
    short_name = models.CharField(max_length=20, blank=True)
    original_name = models.CharField(max_length=200, blank=True, help_text="Name as it appeared in the raw source")
    program_type = models.CharField(max_length=30, choices=ProgramType.choices, blank=True)
    duration = models.CharField(max_length=100, blank=True)
    department = models.ForeignKey(Department, related_name="programs", on_delete=models.CASCADE)
    eligibility = models.TextField(blank=True)
    merit_formula = models.CharField(max_length=200, blank=True)
    shifts = models.JSONField(default=list, blank=True, help_text='e.g. ["Morning", "Afternoon"]')
    fee_group = models.ForeignKey(FeeGroup, null=True, blank=True, related_name="programs", on_delete=models.SET_NULL)
    fee_status = models.CharField(max_length=30, choices=FeeStatus.choices, default=FeeStatus.CONFIRMED)
    verified = models.BooleanField(default=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Transport
# ---------------------------------------------------------------------------
class BusRoute(models.Model):
    route_id = models.PositiveIntegerField(unique=True)
    shift_label = models.CharField(max_length=100, blank=True)
    category = models.CharField(max_length=150, blank=True)
    driver_name = models.CharField(max_length=150, blank=True)
    departure_time = models.TimeField()
    arrival_time = models.TimeField()
    starting_point = models.CharField(max_length=150)
    destination = models.CharField(max_length=150)
    stops = models.JSONField(default=list, help_text="Ordered list of stop names")
    verified = models.BooleanField(default=True)
    notes = models.JSONField(default=list, blank=True, help_text="List of data-quality note strings")

    class Meta:
        ordering = ["departure_time", "route_id"]

    def __str__(self):
        return f"Route {self.route_id}: {self.starting_point} → {self.destination} @ {self.departure_time:%H:%M}"

    @property
    def duration_minutes(self):
        dep = self.departure_time.hour * 60 + self.departure_time.minute
        arr = self.arrival_time.hour * 60 + self.arrival_time.minute
        return arr - dep


# ---------------------------------------------------------------------------
# FAQs
# ---------------------------------------------------------------------------
class FAQ(models.Model):
    faq_id = models.SlugField(max_length=80, unique=True)
    category = models.CharField(max_length=60, default="faq")
    question = models.CharField(max_length=300)
    answer = models.TextField()
    verified = models.BooleanField(default=True)
    note = models.TextField(blank=True)
    expires_on = models.DateField(null=True, blank=True, help_text="For time-bound answers, e.g. an event date")

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ["category", "question"]

    def __str__(self):
        return self.question


# ---------------------------------------------------------------------------
# Chatbot content — mirrors chatbot_chunks.json so it can be edited from the
# CMS instead of by hand-editing the JSON file. A signal/management command
# can re-export this table to chatbot_chunks.json (or push straight to
# ChromaDB) whenever an editor saves a change here.
# ---------------------------------------------------------------------------
class ChatbotChunk(models.Model):
    chunk_id = models.SlugField(max_length=100, unique=True)
    chunk_type = models.CharField(max_length=30)
    category = models.CharField(max_length=60)
    title = models.CharField(max_length=250)
    content = models.TextField(help_text="Exact text shown to the user — keep this self-contained and accurate")
    keywords = models.JSONField(default=list, blank=True, help_text="Roman Urdu / English phrasings for matching")
    source = models.CharField(max_length=100, blank=True)
    verified = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "title"]

    def __str__(self):
        return self.title

    @property
    def search_text(self):
        """Same construction used when the chunks were embedded into ChromaDB."""
        return f"{self.title} | " + "; ".join(self.keywords[:12]) + f" | {self.content}"

"""
Seed the campusinfo app from university_data_clean.json (and, optionally,
chatbot_chunks.json for the ChatbotChunk table).

Usage:
    python manage.py seed_university_data
    python manage.py seed_university_data --data-file /path/to/university_data_clean.json
    python manage.py seed_university_data --chunks-file /path/to/chatbot_chunks.json
    python manage.py seed_university_data --wipe   # delete existing rows first

Re-running is safe: records are matched by their natural slug/id and
updated in place (update_or_create), so you can re-run after editing
the JSON without creating duplicates.
"""
import json
from datetime import datetime
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from campusinfo.models import (
    University, Campus, AdministrationRole, RoleStaffMember, Office,
    Faculty, Department, FeeGroup, Program, BusRoute, FAQ, ChatbotChunk,
)

DEFAULT_DATA_FILE = "university_data_clean.json"
DEFAULT_CHUNKS_FILE = "chatbot_chunks.json"


class Command(BaseCommand):
    help = "Load university_data_clean.json (and optionally chatbot_chunks.json) into the database."

    def add_arguments(self, parser):
        parser.add_argument("--data-file", default=DEFAULT_DATA_FILE)
        parser.add_argument("--chunks-file", default=DEFAULT_CHUNKS_FILE)
        parser.add_argument("--wipe", action="store_true", help="Delete existing rows in this app before seeding")

    def handle(self, *args, **opts):
        data_path = Path(opts["data_file"])
        if not data_path.exists():
            self.stderr.write(self.style.ERROR(f"Data file not found: {data_path}"))
            return
        data = json.loads(data_path.read_text(encoding="utf-8"))

        if opts["wipe"]:
            self.stdout.write("Wiping existing campusinfo rows...")
            for model in (ChatbotChunk, FAQ, BusRoute, Program, FeeGroup, Department, Faculty,
                          Office, RoleStaffMember, AdministrationRole, Campus, University):
                model.objects.all().delete()

        with transaction.atomic():
            self._seed_university(data["university"])
            self._seed_campuses(data.get("campuses", []))
            self._seed_administration(data.get("administration", []))
            self._seed_offices(data)
            fee_groups = self._seed_fee_groups(data.get("fees_2026", {}))
            self._seed_academics(data["academics"], fee_groups)
            self._seed_bus_routes(data.get("transport", {}).get("routes", []))
            self._seed_faqs(data.get("faqs", []))

        self.stdout.write(self.style.SUCCESS("university_data_clean.json loaded."))

        chunks_path = Path(opts["chunks_file"])
        if chunks_path.exists():
            self._seed_chunks(chunks_path)
            self.stdout.write(self.style.SUCCESS(f"{chunks_path.name} loaded into ChatbotChunk."))
        else:
            self.stdout.write(self.style.WARNING(
                f"Chunks file not found at {chunks_path} — skipped ChatbotChunk seeding."
            ))

    # ------------------------------------------------------------------
    def _seed_university(self, u):
        University.objects.update_or_create(
            pk=1,
            defaults=dict(
                name=u["name"],
                short_name=u["short_name"],
                website_domain=u["website_domain"],
                admission_portal_url="https://" + u["admission_portal"] if not u["admission_portal"].startswith("http") else u["admission_portal"],
                vision=u.get("vision", ""),
                mission=u.get("mission", ""),
                goals=u.get("goals", []),
            ),
        )

    def _seed_campuses(self, campuses):
        for c in campuses:
            Campus.objects.update_or_create(
                name=c["name"],
                defaults=dict(address=c.get("address") or "", notes=c.get("notes") or ""),
            )

    def _seed_administration(self, admin_list):
        for a in admin_list:
            role, _ = AdministrationRole.objects.update_or_create(
                role_id=a["role_id"],
                defaults=dict(
                    name=a["name"],
                    designation=a["designation"],
                    responsibilities=a.get("responsibilities", ""),
                ),
            )
            role.staff.all().delete()
            for s in a.get("staff", []):
                RoleStaffMember.objects.create(role=role, designation=s["designation"], name=s["name"])

    def _seed_offices(self, data):
        def upsert(office_type, display_name, **kw):
            Office.objects.update_or_create(office_type=office_type, defaults=dict(display_name=display_name, **kw))

        contact = data.get("contact", {})
        upsert(
            "admission", "Admission / Info Office",
            email=contact.get("email", ""), phone=contact.get("phone", ""),
            phone_local=contact.get("phone_local", ""), phone_intl=contact.get("phone_intl", ""),
            verified=contact.get("verified", True), note=contact.get("note", ""),
            details={"office_address": contact.get("office_address", ""),
                     "admission_steps": data.get("admission", {}).get("steps", [])},
        )

        lib = data.get("library", {})
        lc = lib.get("contact_info", {})
        upsert(
            "library", lib.get("entity", "Central Library"),
            email=lc.get("email", ""), phone=lc.get("phone", ""), hours=lc.get("timings", ""),
            description=lib.get("about_library", {}).get("description", ""),
            details={"facilities": lib.get("facilities", []), "librarian_message": lib.get("librarian_message", {})},
        )

        med = data.get("medical_center", {})
        mc = med.get("contact_info", {})
        upsert(
            "medical", med.get("entity", "Medical Facilitation Center"),
            email=mc.get("email", ""), phone=mc.get("phone", ""), hours=mc.get("clinic_hours", ""),
            description=med.get("about_facility", {}).get("description", ""),
            details={"facilities_and_services": med.get("facilities_and_services", []),
                     "emergency_helpline": mc.get("emergency_helpline", ""),
                     "tagline": med.get("tagline", "")},
        )

        sch = data.get("scholarships", {})
        sc = sch.get("contact_info", {})
        upsert(
            "scholarships", sch.get("entity", "Scholarships & Financial Aid Office"),
            email=sc.get("email", ""), phone=sc.get("phone", ""), hours=sc.get("office_hours", ""),
            description=sch.get("introduction", {}).get("objective", ""),
            details={"available_scholarships": sch.get("available_scholarships", []),
                     "application_process": sch.get("application_process", {})},
        )

        trans = data.get("transport", {}).get("info", {})
        tc = trans.get("contact_info", {})
        upsert(
            "transport", trans.get("entity", "Transport Department"),
            email=tc.get("email", ""), phone=tc.get("phone", ""), hours=tc.get("office_hours", ""),
            contact_person=trans.get("incharge_transport", {}).get("name", ""),
            description=trans.get("about_services", {}).get("description", ""),
            details={"key_features": trans.get("key_features", [])},
        )

        qec = data.get("qec", {})
        upsert(
            "qec", qec.get("entity", "Quality Enhancement Cell"),
            description=qec.get("mission", ""),
            details={"organogram": qec.get("organogram", {}), "vision": qec.get("vision", ""),
                     "core_services": qec.get("core_services", [])},
        )

        fh = data.get("faculty_hostel", {})
        fc = fh.get("contact_info", {})
        upsert(
            "faculty_hostel", fh.get("entity", "Faculty Hostel"),
            phone=fc.get("phone", ""), contact_person=fc.get("contact_person", ""),
            description=fh.get("description", ""),
            details={"facilities": fh.get("facilities", []), "booking_process": fh.get("booking_process", {}),
                     "incharge": fh.get("incharge", {})},
        )

    def _seed_fee_groups(self, fees):
        result = {}
        for gid, fg in fees.items():
            obj, _ = FeeGroup.objects.update_or_create(
                group_id=gid,
                defaults=dict(
                    label=fg["label"],
                    morning_semesters=(fg.get("morning") or {}).get("semesters", []),
                    morning_total=(fg.get("morning") or {}).get("total"),
                    afternoon_semesters=(fg.get("afternoon") or {}).get("semesters", []),
                    afternoon_total=(fg.get("afternoon") or {}).get("total"),
                    verified=(gid != "comp_engineering"),
                ),
            )
            result[gid] = obj
        return result

    def _seed_academics(self, academics, fee_groups):
        for f in academics["faculties"]:
            faculty, _ = Faculty.objects.update_or_create(
                faculty_id=f["faculty_id"], defaults=dict(name=f["name"])
            )
            for d in f["departments"]:
                Department.objects.update_or_create(
                    department_id=d["department_id"],
                    defaults=dict(name=d["name"], faculty=faculty),
                )

        dept_by_id = {d.department_id: d for d in Department.objects.all()}
        for p in academics["programs"]:
            dept = dept_by_id.get(self._slug(p["department"]))
            if dept is None:
                # fall back to matching by name if slug differs slightly
                dept = Department.objects.filter(name=p["department"]).first()
            Program.objects.update_or_create(
                program_id=p["program_id"],
                defaults=dict(
                    name=p["name"],
                    short_name=p.get("short_name") or "",
                    original_name=p.get("original_name", ""),
                    program_type=p.get("type", ""),
                    duration=p.get("duration", ""),
                    department=dept,
                    eligibility=p.get("eligibility") or "",
                    merit_formula=p.get("merit_formula") or "",
                    shifts=p.get("shifts", []),
                    fee_group=fee_groups.get(p.get("fee_group")),
                    fee_status=p.get("fee_status", "confirmed"),
                    verified=p.get("verified", True),
                    note=p.get("note", ""),
                ),
            )

    @staticmethod
    def _slug(s):
        import re
        return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

    def _seed_bus_routes(self, routes):
        for r in routes:
            BusRoute.objects.update_or_create(
                route_id=r["route_id"],
                defaults=dict(
                    shift_label=r.get("shift_label", ""),
                    category=r.get("category", ""),
                    driver_name=r.get("driver_name", ""),
                    departure_time=datetime.strptime(r["departure_time"], "%H:%M").time(),
                    arrival_time=datetime.strptime(r["arrival_time"], "%H:%M").time(),
                    starting_point=r["starting_point"],
                    destination=r["destination"],
                    stops=r.get("stops", []),
                    verified=r.get("verified", True),
                    notes=r.get("notes", []),
                ),
            )

    def _seed_faqs(self, faqs):
        for f in faqs:
            FAQ.objects.update_or_create(
                faq_id=f["faq_id"],
                defaults=dict(
                    question=f["question"],
                    answer=f["answer"],
                    verified=f.get("verified", True),
                    note=f.get("note", ""),
                    expires_on=f.get("expires") or None,
                ),
            )

    def _seed_chunks(self, chunks_path):
        chunks = json.loads(chunks_path.read_text(encoding="utf-8"))
        for c in chunks:
            ChatbotChunk.objects.update_or_create(
                chunk_id=c["id"],
                defaults=dict(
                    chunk_type=c["type"],
                    category=c["category"],
                    title=c["title"],
                    content=c["content"],
                    keywords=c.get("keywords", []),
                    source=c.get("source", ""),
                    verified=c.get("verified", True),
                ),
            )

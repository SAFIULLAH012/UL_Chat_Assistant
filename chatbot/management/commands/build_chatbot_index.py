"""
Build (or rebuild) the local ChromaDB index the chatbot searches, and
warm the intent-classifier embedding cache.

Usage:
    python manage.py build_chatbot_index                  # from chatbot/data/chatbot_chunks.json
    python manage.py build_chatbot_index --source db       # from campusinfo.ChatbotChunk table
    python manage.py build_chatbot_index --chunks-file /path/to/chatbot_chunks.json

Run this once after setup, and again any time chatbot_chunks.json (or the
ChatbotChunk admin table) changes.
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from chatbot.services import vector_store, intent_classifier


class Command(BaseCommand):
    help = "Build the ChromaDB vector index for the chatbot and warm the intent-classifier cache."

    def add_arguments(self, parser):
        parser.add_argument("--source", choices=["file", "db"], default="file")
        parser.add_argument("--chunks-file", default=None, help="Only used with --source file")

    def handle(self, *args, **opts):
        self.stdout.write("Loading embedding model (first run downloads it, ~400MB, needs internet once)...")

        if opts["source"] == "db":
            try:
                from campusinfo.models import ChatbotChunk
            except Exception as exc:
                self.stderr.write(self.style.ERROR(f"campusinfo app not available: {exc}"))
                return
            chunks = []
            for c in ChatbotChunk.objects.all():
                chunks.append({
                    "id": c.chunk_id, "type": c.chunk_type, "category": c.category,
                    "title": c.title, "content": c.content, "source": c.source,
                    "verified": c.verified, "search_text": c.search_text,
                })
            count = vector_store.rebuild_from_chunks(chunks)
        else:
            path = Path(opts["chunks_file"]) if opts["chunks_file"] else None
            count = vector_store.rebuild_from_file(path)

        self.stdout.write(self.style.SUCCESS(f"Indexed {count} chunks into ChromaDB."))

        intent_classifier.warm_cache()
        self.stdout.write(self.style.SUCCESS("Intent classifier cache warmed."))

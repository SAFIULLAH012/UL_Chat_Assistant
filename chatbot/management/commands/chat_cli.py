"""
Interactive terminal chat for testing the pipeline before (or without) a
frontend is wired up. Prints debug info (intent, confidence, entities)
alongside the reply so you can calibrate the thresholds in
chatbot/services/config.py against real questions.

Usage:
    python manage.py chat_cli
    (type 'exit' to quit)
"""
from django.core.management.base import BaseCommand

from chatbot.services.pipeline import process_message


class Command(BaseCommand):
    help = "Interactive terminal chat for testing the offline chatbot pipeline."

    def handle(self, *args, **opts):
        self.stdout.write(self.style.SUCCESS("University of Layyah chatbot - type 'exit' to quit.\n"))
        while True:
            try:
                text = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text.lower() in ("exit", "quit"):
                break

            result = process_message(text)
            self.stdout.write(f"Bot: {result['reply']}\n")
            self.stdout.write(self.style.WARNING(
                f"  [intent={result['intent']} conf={result['intent_confidence']:.2f} "
                f"match_quality={result['match_quality']} chunk={result['matched_chunk_id']} "
                f"entities={[(e['entity_type'], e['canonical']) for e in result['entities']]}]\n"
            ))

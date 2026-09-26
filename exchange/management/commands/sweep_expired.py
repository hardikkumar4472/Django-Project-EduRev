from django.core.management.base import BaseCommand
from exchange.services.proposal_service import ProposalService

class Command(BaseCommand):
    help = "Sweeps past-due exchange proposals and marks them EXPIRED"

    def handle(self, *args, **options):
        count = ProposalService.sweep_expired_proposals()
        self.stdout.write(self.style.SUCCESS(f"Sweep complete. Expired {count} pending proposals."))

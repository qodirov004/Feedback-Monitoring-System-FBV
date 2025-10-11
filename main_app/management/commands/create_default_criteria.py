from django.core.management.base import BaseCommand
from main_app.models import Criterion


class Command(BaseCommand):
    help = 'Create default criteria for evaluation'

    def handle(self, *args, **options):
        default_criteria = [
            {
                'name': 'Uy vazifasi',
                'max_score': 40,
                'is_active': True
            },
            {
                'name': 'Tartib-intizom',
                'max_score': 40,
                'is_active': True
            },
            {
                'name': 'Forma',
                'max_score': 20,
                'is_active': True
            }
        ]

        created_count = 0
        for criterion_data in default_criteria:
            criterion, created = Criterion.objects.get_or_create(
                name=criterion_data['name'],
                defaults={
                    'max_score': criterion_data['max_score'],
                    'is_active': criterion_data['is_active']
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created criterion: {criterion.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Criterion already exists: {criterion.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} new criteria')
        )


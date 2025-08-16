print('Loaded staff_signals')
from django.db.models.signals import post_save
from django.dispatch import receiver
from bank.models import StaffProfile, StaffActivity

@receiver(post_save, sender=StaffProfile)
def handle_staff_profile_changes(sender, instance, created, **kwargs):
    """Handle staff profile changes and log activities."""
    if created:
        StaffActivity.objects.create(
            staff=instance,
            activity_type='staff_managed',
            description=f'New staff member {instance.user.username} added',
            related_object=instance
        )
    if not created and instance.tracker.has_changed('role'):
        old_role = instance.tracker.previous('role')
        StaffActivity.objects.create(
            staff=instance,
            activity_type='staff_managed',
            description=f'Role changed from {old_role} to {instance.role}',
            related_object=instance
        ) 
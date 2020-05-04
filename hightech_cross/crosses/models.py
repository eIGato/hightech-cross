import uuid
from datetime import timedelta

from django.contrib.postgres.fields import JSONField
from django.db import (
    models,
    transaction,
)
from django.utils.timezone import now

PROMPT_PENALTY = timedelta(minutes=15)
WRONG_ANSWER_PENALTY = timedelta(minutes=30)
event_choices = {
    'GET_PROMPT': 'GET_PROMPT',
    'RIGHT_ANSWER': 'RIGHT_ANSWER',
    'WRONG_ANSWER': 'WRONG_ANSWER',
}


class Cross(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=63)
    begins_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    users = models.ManyToManyField('auth.User', related_name='crosses')


class Mission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=63)
    description = models.CharField(max_length=300)
    lattitude = models.DecimalField(max_digits=8, decimal_places=3)
    longitude = models.DecimalField(max_digits=8, decimal_places=3)
    answer = models.CharField(max_length=63)
    cross = models.ForeignKey(
        Cross,
        on_delete=models.CASCADE,
        related_name='missions',
    )
    serial_number = models.SmallIntegerField()

    class Meta:
        unique_together = [
            ('cross', 'serial_number'),
        ]
        ordering = [
            'cross',
            'serial_number',
        ]

    def get_logs(self, user_id):
        return self.progress_logs.filter(user_id=user_id)

    @transaction.atomic
    def get_prompt(self, user_id, serial_number):
        logs = self.get_logs(user_id)
        if logs.filter(
            event=event_choices['GET_PROMPT'],
            details__serial_number=serial_number,
        ).exists():
            return self.prompts.get(serial_number=serial_number)
        if logs.filter(event=event_choices['RIGHT_ANSWER']).exists():
            return None
        prompt = self.prompts.get_object_or_404(serial_number=serial_number)
        log = ProgressLog(
            mission_id=self.id,
            user_id=user_id,
            event=event_choices['GET_PROMPT'],
            details={'serial_number': serial_number},
            penalty=PROMPT_PENALTY,
        )
        log.save()
        return prompt

    @transaction.atomic
    def get_status(self, user_id):
        logs = self.get_logs(user_id)
        prompt_logs = logs.filter(
            event=event_choices['GET_PROMPT'],
        )
        return {
            'finished': logs.filter(
                event=event_choices['RIGHT_ANSWER'],
            ).exists(),
            'answers': list(logs.filter(
                event__in=[
                    event_choices['WRONG_ANSWER'],
                    event_choices['RIGHT_ANSWER'],
                ],
            ).values_list('details__text', flat=True)),
            'prompts': [
                {
                    'serial_number': prompt.serial_number,
                    'text': prompt.text if prompt_logs.filter(
                        details__serial_number=prompt.serial_number,
                    ).exists() else None,
                } for prompt in self.prompts.all()
            ],
            'penalty': logs.aggregate(
                models.Sum('penalty'),
            )['penalty__sum'] or 0,
        }

    @transaction.atomic
    def give_answer(self, user_id, text):
        logs = self.get_logs(user_id)
        if logs.filter(event=event_choices['RIGHT_ANSWER']).exists():
            return True
        if text == self.answer:
            log = ProgressLog(
                mission_id=self.id,
                user_id=user_id,
                event=event_choices['RIGHT_ANSWER'],
                details={'text': text},
                penalty=now() - self.cross.begins_at,
            )
            log.save()
            return True
        if not logs.filter(
            event=event_choices['WRONG_ANSWER'],
            details__text=text,
        ).exists():
            log = ProgressLog(
                mission_id=self.id,
                user_id=user_id,
                event=event_choices['WRONG_ANSWER'],
                details={'text': text},
                penalty=WRONG_ANSWER_PENALTY,
            )
            log.save()
        return False


class Prompt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.CharField(max_length=300)
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='prompts',
    )
    serial_number = models.SmallIntegerField()

    class Meta:
        unique_together = [
            ('mission', 'serial_number'),
        ]


class ProgressLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='progress_logs',
    )
    user = models.ForeignKey(
        'auth.User',
        related_name='progress_logs',
        on_delete=models.CASCADE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    event = models.CharField(max_length=15, choices=event_choices.items())
    details = JSONField()
    penalty = models.DurationField()

    class Meta:
        indexes = [
            models.Index(fields=['created_at'])
        ]
        ordering = [
            'created_at',
        ]

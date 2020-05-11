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


class ProgressEvent(models.TextChoices):
    GET_PROMPT = 'GET_PROMPT'
    RIGHT_ANSWER = 'RIGHT_ANSWER'
    WRONG_ANSWER = 'WRONG_ANSWER'


class Cross(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=63)
    begins_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    users = models.ManyToManyField('auth.User', related_name='crosses')

    @property
    @transaction.atomic
    def leaderboard(self):
        result = []
        for user in self.users.all():
            mission_stati = []
            total_penalty = timedelta(0)
            missions_finished = 0
            for mission in self.missions.all():
                finished = mission.get_finished(user_id=user.id)
                penalty = mission.get_penalty(user_id=user.id)
                mission_stati.append({
                    'sn': mission.sn,
                    'finished': finished,
                })
                total_penalty += penalty * finished
                missions_finished += finished
            result.append({
                'name': user.username,
                'missions': mission_stati,
                'missions_finished': missions_finished,
                'penalty': total_penalty,
            })
        result.sort(key=lambda user: (
            -user['missions_finished'],
            user['penalty'],
        ))
        for rank, user in enumerate(result, 1):
            user['rank'] = rank
        return result


class Mission(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=63)
    description = models.CharField(max_length=300)
    lat = models.DecimalField(max_digits=8, decimal_places=5)
    lon = models.DecimalField(max_digits=8, decimal_places=5)
    answer = models.CharField(max_length=63)
    cross = models.ForeignKey(
        Cross,
        on_delete=models.CASCADE,
        related_name='missions',
    )
    sn = models.SmallIntegerField()

    class Meta:
        unique_together = [
            ('cross', 'sn'),
        ]
        ordering = [
            'cross',
            'sn',
        ]

    def get_logs(self, user_id):
        return self.progress_logs.filter(user_id=user_id)

    @transaction.atomic
    def get_prompt(self, user_id, sn):
        try:
            sn = int(sn)
        except Exception:
            return None
        if not self.cross.begins_at < now() < self.cross.ends_at:
            return None
        logs = self.get_logs(user_id)
        prompt = self.prompts.filter(sn=sn).first()
        if (
            prompt is None
            or logs.filter(
                event=ProgressEvent.GET_PROMPT,
                details__sn=sn,
            ).exists()
            or logs.filter(
                event=ProgressEvent.RIGHT_ANSWER,
            ).exists()
        ):
            return prompt
        log = ProgressLog(
            mission_id=self.id,
            user_id=user_id,
            event=ProgressEvent.GET_PROMPT,
            details={'sn': sn},
            penalty=PROMPT_PENALTY,
        )
        log.save()
        return prompt

    def get_finished(self, user_id):
        return self.get_logs(user_id).filter(
            event=ProgressEvent.RIGHT_ANSWER,
        ).exists()

    def get_penalty(self, user_id):
        return self.get_logs(user_id).aggregate(
            models.Sum('penalty'),
        )['penalty__sum'] or 0

    @transaction.atomic
    def give_answer(self, user_id, text):
        if not self.cross.begins_at < now() < self.cross.ends_at:
            return False
        if self.get_finished(user_id):
            return True
        if text == self.answer:
            log = ProgressLog(
                mission_id=self.id,
                user_id=user_id,
                event=ProgressEvent.RIGHT_ANSWER,
                details={'text': text},
                penalty=now() - self.cross.begins_at,
            )
            log.save()
            return True
        logs = self.get_logs(user_id)
        if not logs.filter(
            event=ProgressEvent.WRONG_ANSWER,
            details__text=text,
        ).exists():
            log = ProgressLog(
                mission_id=self.id,
                user_id=user_id,
                event=ProgressEvent.WRONG_ANSWER,
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
    sn = models.SmallIntegerField()

    class Meta:
        unique_together = [
            ('mission', 'sn'),
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
        on_delete=models.CASCADE,
        related_name='progress_logs',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    event = models.CharField(max_length=15, choices=ProgressEvent.choices)
    details = JSONField()
    penalty = models.DurationField()

    class Meta:
        indexes = [
            models.Index(fields=['created_at'])
        ]
        ordering = [
            'created_at',
        ]

    @property
    def is_right(self):
        return self.event != ProgressEvent.WRONG_ANSWER

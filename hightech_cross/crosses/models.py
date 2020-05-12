"""DB models for `crosses` app.

Attributes:
    PROMPT_PENALTY (timedelta): Time penalty for using prompts.
    WRONG_ANSWER_PENALTY (timedelta): Time penalty for sending wrong answers.
"""
import typing as t
import uuid
from datetime import (
    datetime,
    timedelta,
)
from decimal import Decimal

from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField
from django.db import (
    models,
    transaction,
)
from django.utils.timezone import now

PROMPT_PENALTY = timedelta(minutes=15)
WRONG_ANSWER_PENALTY = timedelta(minutes=30)


class ProgressEvent(models.TextChoices):
    """Progress log event choice namespace."""

    GET_PROMPT = 'GET_PROMPT'
    RIGHT_ANSWER = 'RIGHT_ANSWER'
    WRONG_ANSWER = 'WRONG_ANSWER'


class Cross(models.Model):
    """Tournament for several teams.

    Attributes:
        id (uuid.UUID): Instance PK.
        name (str): Cross title.
        begins_at (datetime): Cross start time.
        ends_at (datetime): Cross end time.
        users (models.Manager): Teams participating.
    """

    id: uuid.UUID = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name: str = models.CharField(max_length=63)
    begins_at: datetime = models.DateTimeField()
    ends_at: datetime = models.DateTimeField()
    users: models.Manager = models.ManyToManyField('auth.User', related_name='crosses')

    @property
    @transaction.atomic
    def leaderboard(self) -> t.List[t.Dict[str, t.Any]]:
        """Ranked team list with stats."""
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
    """Part of a cross.

    Attributes:
        id (uuid.UUID): Instance PK.
        name (str): Mission title.
        description (str): Mission question.
        lat (Decimal): Mission location latitude.
        lon (Decimal): Mission location longitude.
        answer (str): The only right answer for question.
        cross (Cross): Cross the mission is part of.
        sn (int): Mission serial number inside cross.
    """

    id: uuid.UUID = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    name: str = models.CharField(max_length=63)
    description: str = models.CharField(max_length=300)
    lat: Decimal = models.DecimalField(max_digits=8, decimal_places=5)
    lon: Decimal = models.DecimalField(max_digits=8, decimal_places=5)
    answer: str = models.CharField(max_length=63)
    cross: Cross = models.ForeignKey(
        Cross,
        on_delete=models.CASCADE,
        related_name='missions',
    )
    sn: int = models.SmallIntegerField()

    class Meta:
        unique_together = [
            ('cross', 'sn'),
        ]
        ordering = [
            'cross',
            'sn',
        ]

    def get_logs(self, user_id: uuid.UUID) -> models.QuerySet:
        """Get mission logs for given user."""
        return self.progress_logs.filter(user_id=user_id)

    @transaction.atomic
    def get_prompt(
        self,
        user_id: uuid.UUID,
        sn: int,
    ) -> t.Optional['Prompt']:
        """Take mission prompt for user by s/n.

        Return prompt and log this event.
        """
        try:
            sn = int(sn)
        except ValueError:
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

    def get_finished(self, user_id: uuid.UUID) -> bool:
        """Learn if mission is finished."""
        return self.get_logs(user_id).filter(
            event=ProgressEvent.RIGHT_ANSWER,
        ).exists()

    def get_penalty(self, user_id: uuid.UUID) -> timedelta:
        """Get user penalty for mission."""
        return self.get_logs(user_id).aggregate(
            models.Sum('penalty'),
        )['penalty__sum'] or timedelta(0)

    @transaction.atomic
    def give_answer(
        self,
        user_id: uuid.UUID,
        text: str,
    ) -> bool:
        """Try to guess right answer by user."""
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
    """Prompt for mission answer.

    Attributes:
        id (uuid.UUID): Instance PK.
        text (str): Prompt text.
        mission (Mission): Mission the prompt is for.
        sn (int): Prompt serial number inside mission.
    """

    id: uuid.UUID = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    text: str = models.CharField(max_length=300)
    mission: Mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='prompts',
    )
    sn: int = models.SmallIntegerField()

    class Meta:
        unique_together = [
            ('mission', 'sn'),
        ]


class ProgressLog(models.Model):
    """Mission progress log for user/team.

    Attributes:
        id (uuid.UUID): Instance PK.
        mission (Mission): Mission the prompt is for.
        user (auth.User): Progressing team.
        created_at (datetime): Log date.
        event (str): Log event type.
        details (t.Dict[str, t.Any]): Event-specific details.
        penalty (timedelta): Time penalty.
    """

    id: uuid.UUID = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    mission: Mission = models.ForeignKey(
        Mission,
        on_delete=models.CASCADE,
        related_name='progress_logs',
    )
    user: User = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='progress_logs',
    )
    created_at: datetime = models.DateTimeField(auto_now_add=True)
    event: str = models.CharField(max_length=15, choices=ProgressEvent.choices)
    details: t.Dict[str, t.Any] = JSONField()
    penalty: timedelta = models.DurationField()

    class Meta:
        indexes = [
            models.Index(fields=['created_at'])
        ]
        ordering = [
            'created_at',
        ]

    @property
    def is_right(self) -> bool:
        return self.event != ProgressEvent.WRONG_ANSWER

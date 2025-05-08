from django.db import models
from django.utils import timezone

class Robot(models.Model):
    id = models.AutoField(primary_key=True)
    registration_number = models.IntegerField(unique=True, verbose_name='reg_no')
    robot_name = models.CharField(max_length=100)
    author_name = models.CharField(max_length=100)
    author2_name = models.CharField(max_length=100, null=True, blank=True)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=10)    # ISO 3166-2, Aplha-2
    school_name = models.CharField(max_length=100, null=True, blank=True)

    weight = models.IntegerField(null=True, blank=True)
    byebot_points = models.IntegerField(null=True, blank=True)    # match against ByeBot during registration points (0, 1, 2)
    robot_type = models.CharField(max_length=10, null=True, blank=True)    # same ident (e.g. A,B,C) to be used for robots with the same construction
    robot_kit_type = models.CharField(max_length=100, null=True, blank=True)    # e.g. Lego EV3, Lego Spike

    round_group1_qualified = models.IntegerField(default=0, null=True, blank=True, verbose_name='g1')   # group1 (swiss):  0 = not qualified, 1 = qualified
    round_group2_qualified = models.IntegerField(null=True, blank=True, verbose_name='g2')   # group2 (finals): 0 = not qualified, 1 = qualified
    round_group3_qualified = models.IntegerField(null=True, blank=True, verbose_name='g3')

    is_byebot = models.IntegerField(default=0, verbose_name='bye')
    comment = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.robot_name} ({self.country})"

class RoundType(models.TextChoices):
    NONE = 'None', 'None'
    ROUND_ROBIN = 'Round-Robin', 'Round-Robin'
    KNOCKOUT = 'Knockout', 'Knockout'
    SWISS = 'Swiss', 'Swiss'

class Round(models.Model):
    id = models.AutoField(primary_key=True)
    ident = models.CharField(max_length=10, unique=True)     # e.g. R1, F1
    round_type = models.CharField(max_length=20, choices=RoundType.choices, default=RoundType.NONE )  # New, Scheduled, Finished
    name = models.CharField(max_length=100)
    order_index = models.IntegerField(unique=True)

    round_group_index = models.IntegerField(default=0)   # 0 = none, 1 = group1, 2 = group2, 3 = group3

    round_start_time = models.DateTimeField(null=True, blank=True)
    number_of_tables = models.IntegerField(default=4)    # e.g. 3/4

    def __str__(self):
        return f"{self.ident} ({self.name})"

# Enum for match status
class MatchStatus(models.TextChoices):
    NEW = 'New', 'New'
    SCHEDULED = 'Scheduled', 'Scheduled'
    FINISHED = 'Finished', 'Finished'

class Match(models.Model):
    id = models.AutoField(primary_key=True)
    ident = models.CharField(max_length=10, unique=True)  # e.g. R1-M1, R2-M3
    status = models.CharField(max_length=10, choices=MatchStatus.choices, default=MatchStatus.NEW )  # New, Scheduled, Finished
    round = models.ForeignKey('Round', related_name='matches', on_delete=models.CASCADE)  # Reference to Round
    robot1 = models.ForeignKey('Robot', related_name='robot1_matches', on_delete=models.CASCADE)
    robot2 = models.ForeignKey('Robot', related_name='robot2_matches', on_delete=models.CASCADE)
    schedule_time = models.DateTimeField(null=True, blank=True)
    schedule_table = models.IntegerField(null=True, blank=True, verbose_name='table')   # where the match will be played, e.g. value 1 = "Table 1"
    result_robot1_points = models.IntegerField(null=True, blank=True, verbose_name='robot1_points')
    result_robot2_points = models.IntegerField(null=True, blank=True, verbose_name='robot2_points')

    class Meta:
        verbose_name_plural = 'Matches'

    def __str__(self):
        return f"Match {self.ident} - {self.robot1.robot_name} vs {self.robot2.robot_name}"

class RoundResult(models.Model):
    id = models.AutoField(primary_key=True)
    robot = models.ForeignKey('Robot', related_name='round_results', on_delete=models.CASCADE)
    round = models.ForeignKey('Round', related_name='round_results', on_delete=models.CASCADE)  # Reference to Round
    round_robot_points = models.IntegerField(default=0)

    # result points from all rounds with order_index lower or equal to the current round
    round_group1_points = models.IntegerField(null=True, blank=True, verbose_name='g1_points')
    round_group2_points = models.IntegerField(null=True, blank=True, verbose_name='g2_points')
    round_group3_points = models.IntegerField(null=True, blank=True, verbose_name='g3_points')

    total_robot_points = models.BigIntegerField(null=True, blank=True, verbose_name='robot total points')  # g1 + 1000*g2 + 1000000*g3
    total_robot_rank = models.IntegerField(null=True, blank=True, verbose_name='rank')    # 1 = 1st place, 2 = 2nd place...

    total_opponent_points = models.IntegerField(null=True, blank=True, verbose_name="opponents' total points")  # sum of all opponent points that played matches against current robot

    def __str__(self):
        return f"RoundResult {self.robot.robot_name} - {self.round.ident}"

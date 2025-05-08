from django import forms
from .models import Robot, Match

class MatchResultForm(forms.ModelForm):
    class Meta:
        model = Match
        fields = ['status', 'result_robot1_points', 'result_robot2_points']  # Fields for match results

class RobotRegistrationForm(forms.ModelForm):
    class Meta:
        model = Robot
        fields = ['weight', 'byebot_points', 'robot_type', 'robot_kit_type', 'round_group1_qualified']

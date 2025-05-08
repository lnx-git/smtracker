from django.contrib import admin

from .models import Robot

@admin.register(Robot)
class RobotAdmin(admin.ModelAdmin):
    list_display = ('registration_number', 'robot_name', 'author_name', 'city', 'country', 'byebot_points', 'weight', 'robot_type', 'round_group1_qualified', 'round_group2_qualified', 'round_group3_qualified', 'is_byebot', 'comment')
    ordering = ['registration_number']


from .models import Round

@admin.register(Round)
class RoundAdmin(admin.ModelAdmin):
    list_display = ('ident', 'round_type', 'name', 'order_index', 'round_group_index', 'round_start_time', 'number_of_tables')
    ordering = ['order_index']


from .models import Match

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ('ident', 'round', 'robot1', 'robot2', 'result_robot1_points', 'result_robot2_points', 'status', 'schedule_time', 'schedule_table')
    list_filter = ('status', 'round')
    search_fields = ('ident', 'robot1__robot_name', 'robot2__robot_name', 'round__ident')
    ordering = ['ident']

from .models import RoundResult

@admin.register(RoundResult)
class RoundResultAdmin(admin.ModelAdmin):
    list_display = ('round', 'total_robot_rank', 'robot', 'total_robot_points', 'total_opponent_points', 'round_robot_points', 'round_group1_points', 'round_group2_points', 'round_group3_points')
    search_fields = ('round__ident', 'robot__robot_name')
    list_filter = ('round__ident', 'robot__robot_name')
    ordering = ('round', 'total_robot_rank')

from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils import timezone
from django.views import generic
from django.contrib import messages
from django.forms import modelformset_factory

def default_page(request):
    return render(request, 'base_generic.html')

from .models import Robot

def robot_list(request):
    robots = Robot.objects.all()
    return render(request, 'robot_list.html', {'robots': robots})

from .models import Round
from .managers import MatchManager

def round_list(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        selected_ids = request.POST.getlist('selected_rounds')
        match_manager = MatchManager.get_instance()

        for round_id in selected_ids:
            round_obj = Round.objects.get(id=round_id)
            if action == 'generate':
                try:
                    matches = match_manager.generate_for_round(round_obj, request)
                    messages.success(request, f"Matches for round {round_obj.ident} were generated.")
                except ValueError as e:
                    messages.error(request, f"Error generating matches for round {round_obj.ident}: {str(e)}")

            elif action == 'delete':
                try:
                    match_manager.delete_for_round(round_obj, request)
                    messages.success(request, f"Matches for round {round_obj.ident} were deleted.")
                except ValueError as e:
                    messages.error(request, f"Error deleting matches for round {round_obj.ident}: {str(e)}")

            elif action == 'schedule':
                try:
                    match_manager.schedule_matches(round_obj, request)
                    messages.success(request, f"Matches for round {round_obj.ident} were scheduled.")
                except ValueError as e:
                    messages.error(request, f"Error scheduling matches for round {round_obj.ident}: {str(e)}")

        return redirect('smtracker:round_list')

    rounds = Round.objects.all().order_by('order_index')
    for round_obj in rounds:
        # Add a property to each round object to store the number of matches
        round_obj.matches_count = Match.objects.filter(round=round_obj).count()

        # Calculate the count of robots that are qualified for the round
        robots_count = 0
        if round_obj.round_group_index == 1:
            robots_count = Robot.objects.filter(round_group1_qualified=1).count()
        elif round_obj.round_group_index == 2:
            robots_count = Robot.objects.filter(round_group2_qualified=1).count()
        elif round_obj.round_group_index == 3:
            robots_count = Robot.objects.filter(round_group3_qualified=1).count()

        round_obj.robots_count = robots_count

        # Duplicate match detection
        current_matches = Match.objects.filter(round=round_obj)
        current_pairs = set((min(m.robot1_id, m.robot2_id), max(m.robot1_id, m.robot2_id)) for m in current_matches)
    
        previous_matches = Match.objects.filter(
            round__order_index__lt=round_obj.order_index,
            round__round_group_index=round_obj.round_group_index
        )
        previous_pairs = set((min(m.robot1_id, m.robot2_id), max(m.robot1_id, m.robot2_id)) for m in previous_matches)
    
        duplicate_count = len(current_pairs & previous_pairs)
        round_obj.duplicate_matches_count = duplicate_count

        # Number of scheduled matches (both table and start time set)
        round_obj.scheduled_matches_count = Match.objects.filter(
            round=round_obj,
            schedule_table__isnull=False,
            schedule_time__isnull=False
        ).exclude(schedule_table=0).count()
    
    return render(request, 'round_list.html', {'rounds': rounds})
    
from .models import Match
from .forms import MatchResultForm  # MatchResultFormSet

def match_results(request, round_id):
    # Fetch the round and its matches
    round_obj = Round.objects.get(id=round_id)
    matches = Match.objects.filter(round=round_obj).order_by('schedule_table', 'schedule_time', 'ident')

    # Create a formset for match results
    MatchResultFormSet = modelformset_factory(Match, form=MatchResultForm, extra=0)

    if request.method == 'POST':
        match_manager = MatchManager.get_instance()
        formset = MatchResultFormSet(request.POST, queryset=matches)
        if formset.is_valid():
            # Save the results
            try:
                formset.save()
                match_manager.recalculate_round_results(request)
                messages.success(request, "Match results have been saved.")
            except ValueError as e:
                messages.error(request, f"Error saving match results: {str(e)}")

            return redirect('smtracker:round_list')  # Redirect to the rounds list
        else:
            messages.error(request, "Form set is invalid!")
            print(formset.errors)
            print(formset.non_form_errors())

    else:
        formset = MatchResultFormSet(queryset=matches)

    return render(request, 'match_results.html', {'round': round_obj, 'formset': formset})



def scheduled_matches(request, round_id):
    round_obj = get_object_or_404(Round, id=round_id)

    matches = Match.objects.filter(round=round_obj).order_by(
        'schedule_table', 'schedule_time', 'ident'
    )

    return render(request, 'scheduled_matches.html', {'round': round_obj, 'matches': matches})


from .models import RoundResult

def round_results(request, round_id):
    round_obj = get_object_or_404(Round, id=round_id)

    results = RoundResult.objects.filter(round=round_obj).order_by('total_robot_rank')

    return render(request, 'round_results.html', {'round': round_obj, 'results': results})


from .forms import RobotRegistrationForm

def robot_registration_edit(request):
    # fetch queryset
    robots = Robot.objects.all().order_by('registration_number')

    RobotFormSet = modelformset_factory(Robot, form=RobotRegistrationForm, extra=0)
    
    if request.method == 'POST':
        formset = RobotFormSet(request.POST, queryset=robots)
        if formset.is_valid():
            formset.save()
            return redirect('smtracker:robot_registration_edit')
    else:
        formset = RobotFormSet(queryset=robots)

    return render(request, 'robot_registration_formset.html', {'formset': formset})

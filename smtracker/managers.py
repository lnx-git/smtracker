import random
from datetime import timedelta
from django.db import models
from django.contrib import messages
from django.db.models import Q
from .models import Robot, Match, Round, RoundType, RoundResult

class SwissMatchManager:
    _instance = None

    @classmethod
    def get_instance(cls):
        """Ensure only one instance of SwissMatchManager exists."""
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def calculate_tiebreaker_points(self, robots, played_pairs):
        """Custom logic for tiebreaker points."""
        # Implement your logic here
        # For now, return 0 for all
        return {robot.id: 0 for robot in robots}

    def calculate_tiebreaker_points(self, robots, played_pairs, max_depth=6):
        """
        Calculates tiebreaker points for a list of robots based on pairing preferences.
        
        Robots are first sorted by `byebot_points` (descending) and then `weight` (descending). 
        Each robot is paired with the most appropriate opponent from the end of the list 
        (up to `max_depth`), following this priority:
        
            1. A robot with the same `robot_type` (if set).
            2. A robot from a different `country`.
            3. A robot from a different `city`.
            4. Any available robot (fallback).

        Previously played pairings (from `played_pairs`, a set of `(robot1_id, robot2_id)` tuples) are avoided.
        
        Each paired robot receives descending tiebreaker points - the first pair gets the 
        highest scores, decreasing with each pair. Unmatched robots get the remaining points.
        """
        
        # Order robots by byebot_points (desc), then weight (desc)
        sorted_robots = sorted(robots, key=lambda r: (r.byebot_points or 0, r.weight or 0), reverse=True)
        remaining = sorted_robots[:]
        scores = {}
        current_score = len(robots)
    
        while len(remaining) > 1:
            first = remaining.pop(0)
            candidate = None
       
            # Collect possible candidates up to max_depth from the end
            candidates = []
            for i in range(1, min(len(remaining), max_depth) + 1):
                c = remaining[-i]
                pair = (min(first.id, c.id), max(first.id, c.id))
                if pair not in played_pairs:
                    candidates.append(c)
       
            # Priority 1: Same robot_type (if set)
            if first.robot_type:
                for c in candidates:
                    if c.robot_type == first.robot_type:
                        candidate = c
                        break
       
            # Priority 2: Different country
            if not candidate:
                for c in candidates:
                    if c.country != first.country:
                        candidate = c
                        break
       
            # Priority 3: Different city
            if not candidate:
                for c in candidates:
                    if c.city != first.city:
                        candidate = c
                        break
       
            # Fallback: just pick first available
            if not candidate and candidates:
                candidate = candidates[0]
       
            if candidate:
                scores[first.id] = current_score
                scores[candidate.id] = current_score - 1
                remaining.remove(candidate)
                current_score -= 2
            else:
                # No valid match found
                scores[first.id] = current_score
                current_score -= 1
       
        if remaining:
            last_robot = remaining[0]
            scores[last_robot.id] = current_score
       
        return scores
       

    def generate_for_round(self, round_obj, request=None):
        """
        Swiss-style Match Generation Rules:        

        - Eligibility: 
            - Only robots marked as qualified for the current round group (ByeBot excluded) are eligible for pairing.        

        - Ordering:
            - Robots are ranked by descending total points and opponent points.
            - Robots tied on both metrics may be re-ordered using custom "tiebreaker points" to ensure more balanced matchups.        

        - Match Pairing Constraints:
            - Each selected robot is paired with the best available robot whose performance is worse than its.        
            - Robots must not be paired against the same opponent more than once within the same round group.

        - ByeBot Match:
            - If the number of eligible robots is odd, the worst robot who hasn't yet played the ByeBot will be assigned a ByeBot match.

        - Pair Selection:
            - Robots are paired sequentially from the top of the ranking list.
            - For each robot, the first available opponent (lower in ranking) that satisfies the pairing constraints is chosen.
            - If no valid opponent is found due to prior matches, a fallback ByeBot match is assigned with a warning.        
        """
        group_index = round_obj.round_group_index

        # Step 1: Determine previous round
        previous_round = Round.objects.filter(
            order_index__lt=round_obj.order_index,
            round_group_index=group_index
        ).order_by('-order_index').first()
        previous_results = RoundResult.objects.filter(round=previous_round) if previous_round else RoundResult.objects.none()

        # Step 2: Determine eligible robots
        if group_index == 1:
            robots = Robot.objects.filter(round_group1_qualified=1, is_byebot=0)
        elif group_index == 2:
            robots = Robot.objects.filter(round_group2_qualified=1, is_byebot=0)
        elif group_index == 3:
            robots = Robot.objects.filter(round_group3_qualified=1, is_byebot=0)
        else:
            robots = Robot.objects.filter(is_byebot=0)

        # Step 3: Determine robots who have already played against a byebot
        byebot = Robot.objects.filter(is_byebot=1).first()
        if byebot:
            byebot_id = byebot.id
            byebot_matches = (
                Match.objects.filter(
                    round__order_index__lt=round_obj.order_index, round__round_group_index=group_index, robot1_id=byebot_id
                ) |
                Match.objects.filter(
                    round__order_index__lt=round_obj.order_index, round__round_group_index=group_index, robot2_id=byebot_id
                )
            )
            robots_vs_byebot_ids = set(byebot_matches.values_list('robot1_id', flat=True)) | set(byebot_matches.values_list('robot2_id', flat=True))
            robots_vs_byebot_ids.discard(byebot_id)
        else:
            byebot_id = None
            robots_vs_byebot_ids = set()

        messages.debug(request, f"SwissMatchManager.generate_for_round(): robots_vs_byebot_ids = {robots_vs_byebot_ids}")

        # Step 4: Combine data with results
        robot_data = []
        results_map = {res.robot_id: res for res in previous_results}

        for robot in robots:
            result = results_map.get(robot.id)
            if result:
                robot_data.append({
                    'robot': robot,
                    'total_points': result.total_robot_points or 0,
                    'opponent_points': result.total_opponent_points or 0,
                    'tiebreaker_points': 0,
                    'played_byebot': robot.id in robots_vs_byebot_ids
                })
            else:
                robot_data.append({
                    'robot': robot,
                    'total_points': 0,
                    'opponent_points': 0,
                    'tiebreaker_points': 0,
                    'played_byebot': 0
                })

        # Step 5: Sort robots (total_points desc, opponent_points desc)
        robot_data.sort(key=lambda x: (-x['total_points'], -x['opponent_points']))

        messages.debug(request, f"SwissMatchManager.generate_for_round(): robot_data_len = {len(robot_data)}")

        # Step 6: Handle odd number by assigning byebot match 
        match_cnt = 0
        if len(robot_data) % 2 == 1:
            for robot in reversed(robot_data):  # Iterate from the worst to the best
                if not robot['played_byebot']:
                    Match.objects.create(
                        round=round_obj,
                        ident=f"{round_obj.ident}-M99",
                        robot1=robot['robot'],
                        robot2_id=byebot_id,
                        status="Scheduled"
                    )
                    match_cnt += 1
                    robot_data.remove(robot)
                    break

        # Build a set of (robot1_id, robot2_id) tuples that already played in this group
        previous_matches = Match.objects.filter(round__order_index__lt=round_obj.order_index, round__round_group_index=group_index)
        played_pairs = set()
        for match in previous_matches:
            a, b = match.robot1_id, match.robot2_id
            played_pairs.add((min(a, b), max(a, b)))

        # Step 7: Handle tiebreakers
        i = 0
        while i < len(robot_data):
            j = i + 1
            while (j < len(robot_data) and
                   robot_data[j]['total_points'] == robot_data[i]['total_points'] and
                   robot_data[j]['opponent_points'] == robot_data[i]['opponent_points']):
                j += 1
            # calculate tiebreaker_points only for groups of 3 and more robots
            if j - i > 2:
                tied_group = robot_data[i:j]
                tiebreaker_points = self.calculate_tiebreaker_points([r['robot'] for r in tied_group], played_pairs)
                for data in tied_group:
                    data['tiebreaker_points'] = tiebreaker_points.get(data['robot'].id, 0)
                robot_data[i:j] = sorted(tied_group, key=lambda x: -x['tiebreaker_points'])
            i = j

        # debug: print robot data
        for d in robot_data:
            messages.debug(request, f"SwissMatchManager.generate_for_round(): robot {d['robot'].robot_name} ({d['robot'].registration_number}): total_points = {d['total_points']}, opponent_points = {d['opponent_points']}, tiebreaker_points = {d['tiebreaker_points']}, {d['robot'].city}, {d['robot'].country}, b: {d['robot'].byebot_points}, w: {d['robot'].weight}, t: {d['robot'].robot_type}")

        # Step 8: Pair and create matches
        matches = []
        match_id = 1  # only used for ident generation
        group_index = round_obj.round_group_index
                
        # Create a working list of robot instances
        remaining = [r['robot'] for r in robot_data]
        paired_ids = set()
        
        while len(remaining) >= 1:
            r1 = remaining[0]
            found = False
            for i in range(1, len(remaining)):
                r2 = remaining[i]

                pair = (min(r1.id, r2.id), max(r1.id, r2.id))
                if pair in played_pairs:
                    messages.debug(request, f"SwissMatchManager.generate_for_round: skipping duplicate match: {r1.robot_name} vs {r2.robot_name}...")
                    continue

                # Create match
                match = Match.objects.create(
                    round=round_obj,
                    ident=f"{round_obj.ident}-M{(match_id):02d}",
                    robot1=r1,
                    robot2=r2,
                    status="Scheduled"
                )
                matches.append(match)
                match_id += 1
                match_cnt += 1
                played_pairs.add(pair)
                # Remove both from list
                remaining.pop(i)
                remaining.pop(0)
                found = True
                break

            if not found:
                # No valid opponent found for r1
                messages.error(request, f"Error: SwissMatchManager: No valid opponent found for {r1.robot_name}, adding duplicate match with ByeBot!")
                # Add extra match against ByeBot -> violation of rules(?)
                match = Match.objects.create(
                    round=round_obj,
                    ident=f"{round_obj.ident}-M{(match_id):02d}",
                    robot1=r1,
                    robot2=byebot,
                    status="Scheduled"
                )
                matches.append(match)
                match_id += 1
                match_cnt += 1
                remaining.pop(0)

        messages.success(request, f"SwissMatchManager: {match_cnt} matches for round {round_obj.ident} were created.")

        return matches

class MatchManager(models.Manager):
    _instance = None

    @classmethod
    def get_instance(cls):
        """Ensure only one instance of MatchManager exists."""
        if not cls._instance:
            cls._instance = cls()
        return cls._instance

    def generate_for_round(self, round_obj, request=None):
        """Generate matches based on the round_type from the round_obj."""
        round_type = round_obj.round_type  # Get round type directly from the round object
        
        if round_type == RoundType.SWISS:
            match_manager = SwissMatchManager.get_instance()
        elif round_type == RoundType.ROUND_ROBIN:
            # Implement round-robin logic here
            pass
        elif round_type == RoundType.KNOCKOUT:
            # Implement knockout logic here
            pass
        else:
            raise ValueError("Unsupported round type")

        matches = match_manager.generate_for_round(round_obj, request)
        return matches

    def delete_for_round(self, round_obj, request=None):
        """Delete matches."""
        match_count = Match.objects.filter(round=round_obj).delete()[0]

        if request is not None:
            if match_count > 0:
                messages.success(request, f"{match_count} matches for round {round_obj.ident} were deleted.")
            else:
                messages.warning(request, f"Warning: No matches found for round {round_obj.ident} to delete.")

        return match_count

    def schedule_matches(self, round_obj, request=None, match_time_mins=4):

        if not round_obj.round_start_time or not round_obj.number_of_tables:
            if request:
                messages.error(request, f"Error: Missing start time or number of tables for round {round_obj.ident}!")
            return []
    
        matches = Match.objects.filter(round=round_obj).order_by('ident')
        table_count = round_obj.number_of_tables
        table_times = [round_obj.round_start_time for _ in range(table_count)]
    
        for i in range(0, len(matches), table_count):
            group = matches[i:i+table_count]
            available_tables = list(range(1, table_count + 1))
            random.shuffle(available_tables)
    
            for match, table_number in zip(group, available_tables):
                match.schedule_time = table_times[table_number - 1]
                match.schedule_table = table_number
                match.save()
    
                # Add 5 minutes after each match for this table
                table_times[table_number - 1] += timedelta(minutes=match_time_mins)
    
        return matches
    
    def calculate_opponent_points(self, request=None):
        """recalculate opponent points for every round and every robot"""

        rounds = Round.objects.all().order_by('order_index')


        for round_obj in rounds:
            previous_rounds = Round.objects.filter(order_index__lte=round_obj.order_index, round_group_index=round_obj.round_group_index)

            # For each robot in this round
            results = RoundResult.objects.filter(round=round_obj)
            for result in results:
                robot = result.robot

                # Get matches of this robot from previous rounds
                matches = Match.objects.filter(round__in=previous_rounds).filter(
                    Q(robot1=robot) | Q(robot2=robot)
                )

                opponent_ids = set()
                for match in matches:
                    opponent = None
                    if match.robot1 == robot:
                        opponent = match.robot2
                    elif match.robot2 == robot:
                        opponent = match.robot1

                    if opponent.id != robot.id and opponent.is_byebot != 1:
                        opponent_ids.add(opponent.id)

                #if robot.id == 6 and round.ident == 'R2':
                #messages.debug(request, f"MatchManager.calculate_opponent_points(): round_ident = {round_obj.ident}, robot_id = {robot.id}, opponent_ids = {opponent_ids}")

                # Sum the points of those opponents in current round
                total_opponent_points = RoundResult.objects.filter(
                    round=round_obj,
                    robot__id__in=opponent_ids
                ).aggregate(total=models.Sum('total_robot_points'))['total'] or 0

                # Update the result
                result.total_opponent_points = total_opponent_points
                result.save()

        messages.success(request, f"Opponent points were recalculated.")

    def calculate_ranks_for_rounds(self, request=None):

        rounds = Round.objects.all().order_by('order_index')

        for round_obj in rounds:
            # Sort the RoundResults by total_robot_points in descending order
            round_results = RoundResult.objects.filter(round=round_obj).order_by('-total_robot_points', '-total_opponent_points')
        
            # Assign ranks to each result based on the sorted order
            rank = 1
            for round_result_obj in round_results:
                round_result_obj.total_robot_rank = rank
                round_result_obj.save()
                rank += 1

        messages.success(request, f"Robot ranks were recalculated.")
        
        return (rank - 1)

    def calculate_ranks_for_rounds(self, request=None):
        rounds = Round.objects.all().order_by('order_index')
    
        for round_obj in rounds:
            # Sort results by total_robot_points and total_opponent_points, both descending
            round_results = RoundResult.objects.filter(round=round_obj).order_by('-total_robot_points', '-total_opponent_points')
    
            rank = 1
            prev_points = None
            prev_opponent_points = None
            tie_rank = rank  # store the rank to assign in case of tie
    
            for round_result_obj in round_results:
                # Check for tie with previous result
                if prev_points is not None and (
                    round_result_obj.total_robot_points == prev_points and
                    round_result_obj.total_opponent_points == prev_opponent_points
                ):
                    round_result_obj.total_robot_rank = tie_rank  # assign the same rank
                else:
                    tie_rank = rank  # update tie_rank to current rank
                    round_result_obj.total_robot_rank = rank
                    prev_points = round_result_obj.total_robot_points
                    prev_opponent_points = round_result_obj.total_opponent_points
    
                round_result_obj.save()
                rank += 1
    
        messages.success(request, f"Robot ranks were recalculated.")
        return (rank - 1)

    def recalculate_round_results(self, request=None):
        """recalculate_round_results."""

        result_cnt = 0
        RoundResult.objects.all().delete()
        
        robots = Robot.objects.all()
        rounds = Round.objects.all().order_by('order_index')

        for robot in robots:

            group1_points = 0
            group2_points = 0
            group3_points = 0

            calc_byebot = 1
            for round_obj in rounds:

                group_index = round_obj.round_group_index

                # Check qualification
                if group_index == 1 and not robot.round_group1_qualified:
                    continue
                if group_index == 2 and not robot.round_group2_qualified:
                    continue
                if group_index == 3 and not robot.round_group3_qualified:
                    continue

                # Matches in the specific round
                matches = (
                    Match.objects.filter(round=round_obj).filter(robot1=robot) | 
                    Match.objects.filter(round=round_obj).filter(robot2=robot)
                )
        
                round_points = 0
                for match in matches:
                    points = 0
                    if match.robot1 == robot:
                        points = match.result_robot1_points or 0
                    elif match.robot2 == robot:
                        points = match.result_robot2_points or 0
                    # calculate only points for the first match with ByeBot
                    if (robot.is_byebot == 0) and (match.robot1.is_byebot == 1 or match.robot2.is_byebot == 1):
                        if calc_byebot == 0:
                            points = 0
                            messages.warning(request, f"Warning: MatchManager.recalculate_round_results: multiple matches with ByeBot found in round {round_obj.ident} for {robot.robot_name}, points ignored!")
                        calc_byebot = 0
                    round_points += points

                # The ByeBot must never score any points in the round results (to ensure it remains in last place)
                if robot.is_byebot == 1:
                    round_points = -1

                match round_obj.round_group_index:
                    case 1:
                        group1_points += round_points
                    case 2:
                        group2_points += round_points
                    case 3:
                        group3_points += round_points

                if robot.is_byebot == 1:
                    group1_points = -1
                    group2_points = -1
                    group3_points = -1

                total_points = ( group1_points + 1000 * group2_points + 1000000 * group3_points )

                if robot.is_byebot == 1:
                    total_points = -1
        
                RoundResult.objects.create(
                    robot=robot,
                    round=round_obj,
                    round_robot_points = round_points,
                    round_group1_points = group1_points,
                    round_group2_points = group2_points,
                    round_group3_points = group3_points,
                    total_robot_points = total_points,
                )

                result_cnt += 1

        messages.success(request, f"Round results were recalculated.")

        self.calculate_opponent_points(request)
        self.calculate_ranks_for_rounds(request)

        return result_cnt

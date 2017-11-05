from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.http import HttpResponseNotAllowed
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.shortcuts import render

# Create your views here.

# TODO: performance optimization: select_related() and prefetch_related()
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import CreateView

from .models import *
from .forms import *


# NOTE: message alert tags: primary, success, danger, warning, info (https://getbootstrap.com/docs/4.0/components/alerts/)

@login_required
def index(request):
    game = Game.objects.get_current()
    player = None
    date_next_quota_check = None
    if game:
        player = request.user.players.get_or_none(game=game)
        if game.has_started:  # TODO: store "next quota check' date in model for better performance; update on every quota check
            days_elapsed = game.length
            days_until_next_quota_check = game.quota_period_days - (days_elapsed % game.quota_period_days)
            date_next_quota_check = date.today() + timedelta(days=days_until_next_quota_check)
    elif not request.user.is_superuser:
        messages.add_message(request, messages.INFO, "Currently no ongoing games. Check back later.", extra_tags='primary')

    if game and game.has_started:
        if not game.has_ended:
            if player:
                if player.dead:
                    messages.add_message(request, messages.INFO, "You have been eliminated.", extra_tags='primary')  # TODO: "if you believe this is an error, contact the game admin (Ben Bradley)"
            elif not request.user.is_superuser:
                messages.add_message(request, messages.INFO, "The game has already started. Contact an admin if you would like to join.", extra_tags='warning')
        else:
            messages.add_message(request, messages.INFO, "The game has ended! See results below.", extra_tags='primary')


    context = {
        'game': game,
        'player': player,
        'date_next_quota_check': date_next_quota_check,
    }

    return render(request, 'main/index.html', context)

def user_login(request):
    if request.method == 'POST':
        login_form = LoginForm(data=request.POST)
        next_page = request.POST.get('next_page', reverse('index'))
        if login_form.is_valid():
            username = login_form.cleaned_data['username']
            password = login_form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return HttpResponseRedirect(next_page)
            else:
                messages.add_message(request, messages.INFO, "Invalid login credentials or account does not exist", extra_tags='danger')
    else:
        login_form = LoginForm()
        next_page = request.GET.get('next', reverse('index'))

    context = {
        'login_form': login_form,
        'next_page': next_page,
    }

    return render(request, 'main/login.html', context)

@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('index'))

def register(request):
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)
        if user_form.is_valid() and profile_form.is_valid():  # TODO: ensure that users and profile are always one-to-one (sync with signals?)
            user = user_form.save()
            user.set_password(user.password)
            user.save()
            profile_form = UserProfileForm(instance=user.profile, data=request.POST)
            profile_form.save()
            login(request, user)
            messages.add_message(request, messages.INFO, "Successfully registered", extra_tags='success')
            return HttpResponseRedirect(reverse('index'))
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()

    context = {
        'user_form': user_form,
        'profile_form': profile_form,
    }

    return render(request, 'main/register.html', context)

@login_required
def user_update(request):
    if request.method == 'POST':
        form = UserUpdateForm(data=request.POST)
        if form.is_valid():
            user = request.user
            user.email = form.cleaned_data['email']
            user.profile.phone_num = form.cleaned_data['phone_num']
            user.save()
            user.profile.save()
            messages.add_message(request, messages.INFO, "Successfully updated user", extra_tags='success')
            return HttpResponseRedirect(reverse('index'))
    else:
        user = request.user
        form = UserUpdateForm(initial={'phone_num': user.profile.phone_num, 'email': user.email})

    context = {
        'form': form,
    }

    return render(request, 'main/user_update.html', context)

@login_required
def join_game(request):  # TODO: request must be POST?
    game = Game.objects.get_current()
    if game:
        if not game.has_started:
            if not request.user.players.filter(game=game).exists():
                game.add_player(request.user)
                messages.add_message(request, messages.INFO, "Successfully joined game", extra_tags='success')
            else:
                # TODO: print error that user has already joined the game
                messages.add_message(request, messages.INFO, "Already joined game", extra_tags='warning')
        else:
            # TODO: print error that game has already started
            messages.add_message(request, messages.INFO, "Game has already started", extra_tags='danger')
    return HttpResponseRedirect(reverse('index'))

@login_required
def leave_game(request):  # TODO: request must be POST?
    game = Game.objects.get_current()
    if game:
        if not game.has_started:
            if request.user.players.filter(game=game).exists():
                game.remove_player(request.user)
                messages.add_message(request, messages.INFO, "Successfully left game", extra_tags='warning')
            else:
                # TODO: print error that user has already joined the game
                messages.add_message(request, messages.INFO, "Already left game", extra_tags='warning')
        else:
            # TODO: print error that game has already started
            messages.add_message(request, messages.INFO, "Game has already started", extra_tags='danger')
    return HttpResponseRedirect(reverse('index'))


@method_decorator(staff_member_required, name='dispatch')
class GameCreate(CreateView):
    model = Game
    fields = ['date_start', 'twilio_phone_num', 'twilio_account_sid', 'twilio_auth_token']
    template_name_suffix = '_create'
    success_url = reverse_lazy('index') # TODO: create an actual success page/template for each of these generic views?


@staff_member_required
def create_game(request):
    if request.method == 'POST':
        game = Game.objects.get_current()
        if game:
            if not game.has_ended:
                messages.add_message(request, messages.INFO, "Cannot start a new game until the current game has ended.", extra_tags='danger')
                return HttpResponseRedirect(reverse('index'))
            else:
                game.close()
        game_form = GameForm(data=request.POST)
        if game_form.is_valid():
            game = game_form.save(commit=False)
            game.admin = request.user
            game.save()
            messages.add_message(request, messages.INFO, "Successfully created game", extra_tags='success')
            return HttpResponseRedirect(reverse('index'))
    else:
        game_form = GameForm()

        context = {
            'game_form': game_form,
        }

        return render(request, 'main/game_create.html', context)

@staff_member_required
def update_game(request):
    game = Game.objects.get_current()
    if request.method == 'POST':
        game_form = GameForm(instance=game, data=request.POST)
        if game_form.is_valid():
            game = game_form.save()
            messages.add_message(request, messages.INFO, "Successfully updated game", extra_tags='success')
            return HttpResponseRedirect(reverse('index'))
    else:
        game_form = GameForm(instance=game)

    context = {
        'game_form': game_form,
    }

    return render(request, 'main/game_update.html', context)


@staff_member_required
def start_game(request):  # TODO: make this automatic with scheduled jobs
    game = Game.objects.get_current()
    if game:
        if game.has_started:
            messages.add_message(request, messages.INFO, "Game has already started", extra_tags='warning')
        else:
            succeeded = game.start()
            if succeeded:
                messages.add_message(request, messages.INFO, "Game started!", extra_tags='success')
            else:
                messages.add_message(request, messages.INFO, "Cannot start a game with less than 2 players", extra_tags='danger')
    else:
        messages.add_message(request, messages.INFO, "No ongoing game found. Please create a new game before starting", extra_tags='warning')
    return HttpResponseRedirect(reverse('index'))


@staff_member_required
def close_game(request):
    game = Game.objects.get_current()
    if game:
        if request.method == 'POST':
            if game.has_ended:
                messages.add_message(request, messages.INFO, "Game closed", extra_tags='success')
            else:
                messages.add_message(request, messages.INFO, "Game cancelled", extra_tags='success')
            game.close()
        else:
            context = {
                'game': game,
            }
            return render(request, 'main/confirm_close_game.html', context)
    else:
        messages.add_message(request, messages.INFO, "No ongoing game", extra_tags='danger')
    return HttpResponseRedirect(reverse('index'))

@login_required
def killed_target(request):
    game = Game.objects.get_current()
    if game:
        player = request.user.players.get_or_none(game=game)
        if player:
            target = player.target
            if target:
                if request.method == 'POST':
                    server_state = ServerState.load()
                    if server_state.elimination_in_progress:
                        messages.add_message(request, messages.INFO, "Server is busy. Try again later.", extra_tags='warning')
                    else:
                        server_state.elimination_in_progress = True
                        server_state.save()
                        player.eliminate_target()
                        server_state.elimination_in_progress = False
                        server_state.save()
                        messages.add_message(request, messages.INFO, "Target eliminated: " + str(target), extra_tags='success')
                else:
                    context = {
                        'target': target,
                    }
                    return render(request, 'main/confirm_killed_target.html', context)
        else:
            messages.add_message(request, messages.INFO, "No player info found", extra_tags='danger')
    else:
        messages.add_message(request, messages.INFO, "No ongoing game", extra_tags='danger')
    return HttpResponseRedirect(reverse('index'))

@login_required
def killed_attacker(request):
    # TODO: security: in case user enters url manually - don't allow this to run unless there are 10 or fewer players left in the game
    game = Game.objects.get_current()
    if game:
        player = request.user.players.get_or_none(game=game)
        if player:
            attacker = player.attacker
            if attacker:
                if request.method == 'POST':
                    server_state = ServerState.load()
                    if server_state.elimination_in_progress:
                        messages.add_message(request, messages.INFO, "Server is busy. Try again later.", extra_tags='warning')
                    else:
                        server_state.elimination_in_progress = True
                        server_state.save()
                        player.eliminate_attacker()
                        server_state.elimination_in_progress = False
                        server_state.save()
                        messages.add_message(request, messages.INFO, "Attacker eliminated: " + str(attacker), extra_tags='success')
                else:
                    context = {
                        'attacker': attacker,
                    }
                    return render(request, 'main/confirm_killed_attacker.html', context)
        else:
            messages.add_message(request, messages.INFO, "No player info found", extra_tags='danger')
    else:
        messages.add_message(request, messages.INFO, "No ongoing game", extra_tags='danger')
    return HttpResponseRedirect(reverse('index'))

@staff_member_required
def elimination_undo(request, pk):
    e = Elimination.objects.get(pk=pk)
    if request.method == 'POST':
        server_state = ServerState.load()
        if server_state.revert_in_progress:
            messages.add_message(request, messages.INFO, "Server is busy. Try again later.", extra_tags='warning')
        else:
            server_state.revert_in_progress = True
            server_state.save()
            num_eliminations = e.revert()
            server_state.revert_in_progress = False
            server_state.save()
            messages.add_message(request, messages.INFO, "Successfully reverted " + str(num_eliminations) + " eliminations", extra_tags='success')
        return HttpResponseRedirect(reverse('index'))
    else:
        context = {
            'elimination': e,
        }
        return render(request, 'main/confirm_elimination_undo.html', context)

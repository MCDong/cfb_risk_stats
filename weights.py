import copy
import os
import math
import json
import scipy.optimize

days_data = {}
_dir = 'data'

team_data = {}
team_list = []
zeroes = [0,0,0,0,0]

_file_list = sorted(os.listdir(_dir), key=lambda x: int(x.split('.')[0].split('votes')[1]))
territory_history = {}
for fname in _file_list:
    day = int(fname.split('.')[0].split('votes')[1])
    with open("{}/{}".format(_dir, fname)) as f:
        for line in f.readlines():
            line = line.split(',')            
            team = line[2].strip("\"")
            territory = line[3].strip("\"")
            mvp = int(line[-1][1])
            if not team or not territory:
                continue
            if territory not in territory_history:
                territory_history[territory] = [territory]
            if mvp:
                territory_history[territory].append(team)
        for territory in territory_history:
            if len(territory_history[territory]) < day:
                territory_history[territory].append(territory_history[territory][-1])

texas_players = {}
for fname in _file_list:
    if '.csv' not in fname:
        continue
    day = int(fname.split('.')[0].split('votes')[1])
    if day < 12:
        continue
    days_data[day] = {}
    team_data[day] = {}
    with open("{}/{}".format(_dir, fname)) as f:
        for line in f.readlines():
            line = line.split(',')
            name = line[1].strip("\"")
            team = line[2].strip("\"")
            territory = line[3].strip("\"")
            stars = int(line[4].strip("\""))
            mvp = int(line[-1][1])
            if not team or not territory:
                continue
            if day < 12:
                multiplier = float(line[5].strip("\""))
                if multiplier == 0:
                    zeroes[stars - 1] += 1
            if team == 'Texas':
                if name not in texas_players:
                    texas_players[name] = {'days': [], 'stars': 0}
                texas_players[name]['days'].append(day)
                if stars > texas_players[name]['stars']:
                    texas_players[name]['stars'] = stars
            if name in texas_players and team != 'Texas':
                texas_players.pop(name)
            
            if territory not in days_data[day]:
                days_data[day][territory] = {'stars': [0,0,0,0,0], 'chaos_stars':[0,0,0,0,0], 'home2x_stars':[0,0,0,0,0], 'mvp': 0}
            if team == 'Chaos':
                days_data[day][territory]['chaos_stars'][stars - 1] += 1                
            elif team == territory:
                last_owner = territory_history[territory][day - 1]
                if last_owner == team:
                    days_data[day][territory]['home2x_stars'][stars - 1] += 1
                else:
                    days_data[day][territory]['stars'][stars - 1] += 1
            else:
                days_data[day][territory]['stars'][stars - 1] += 1
        
            if mvp:
                days_data[day][territory]['mvp'] = stars - 1

            if team not in team_data[day]:
                team_data[day][team] = {'stars':[0,0,0,0,0]}
                team_list.append(team)
            team_data[day][team]['stars'][stars - 1] += 1

for day in team_data:
    for team in team_data[day]:
        team_data[day][team]['total_players'] = sum(team_data[day][team]['stars'])
all_data = []
all_stars = [0,0,0,0,0]
actual = [0,0,0,0,0]
territory_count = 0
discarded_count = 0
for day in days_data:
    for territory in days_data[day]:
        if sum(days_data[day][territory]['chaos_stars']) > 0:
            discarded_count += 1
            continue
        if sum(days_data[day][territory]['stars']) + sum(days_data[day][territory]['home2x_stars']) < 20:
            discarded_count += 1            
            continue
        # if sum(days_data[day][territory]['home2x_stars']) > 0:
        #     discarded_count += 1                        
        #     continue
        all_data.append(days_data[day][territory])
        territory_count += 1        
        actual[days_data[day][territory]['mvp']] += 1 
        for i in range(5):
            all_stars[i] += days_data[day][territory]['stars'][i]

print(territory_count, discarded_count, actual)

dfw = [0,0,0,0,0]
first = 1

def find_diff(weights, all_data=all_data, actual=actual, rnd=False):
    for j in list(range(5)):
        sum_buckets = 0
        for t in all_data:
            stars = t['stars']
            chaos_stars = t['chaos_stars']
            home_stars = t['home2x_stars']
            j_strength = stars[j] * weights[j]
            j_chaos = chaos_stars[j] * 1. * weights[j]
            j_home = home_stars[j] * 2. * weights[j]
            j_total = j_strength + j_chaos + j_home

            i_strength = sum([stars[i] * weights[i] for i in range(5)])
            i_chaos = sum([chaos_stars[i] * 1. * weights[i] for i in range(5)])
            i_home = sum([home_stars[i] * 2. * weights[i] for i in range(5)])
            i_total = i_strength + i_chaos + i_home
            try:
                p = j_total / i_total
            except ZeroDivisionError:
                p = 0

            sum_buckets += p
        if rnd:
            dfw[j] = round(sum_buckets)
        else:
            dfw[j] = sum_buckets

    diff = [actual[x] - dfw[x] for x in range(5)]
    return diff

def output_lst(lst, pct=False, ret=False):
    if pct:
        out = json.dumps({'%s*' % str(x+1) : "%s%%" % str(lst[x]*100) for x in range(5)}, sort_keys=True)
    else:
        out = json.dumps({'%s*' % str(x+1) : lst[x] for x in range(5)}, sort_keys=True)
    if ret:
        return out
    print(out)

def pen(x, all_data, actual, rnd):
    res = find_diff(x.tolist(), all_data, actual, rnd)
    r = sum([x**2 for x in res])
    return r

def handicap_zeroes(_leg=.85, _leg2=1.):
    ac = copy.deepcopy(actual)
    ad = copy.deepcopy(all_data)
    for t in ad:
        t['stars'][0] = _leg * t['stars'][0]
        t['chaos_stars'][0] = _leg * t['chaos_stars'][0]
        t['stars'][1] = _leg2 * t['stars'][1]
        t['chaos_stars'][1] = _leg2 * t['chaos_stars'][1]
        
    return (ad, ac)

def pen2(x, weights):
    ad, ac = handicap_zeroes(x[0], x[1])
    res = find_diff(weights, ad, ac, False)
    
    return sum([i**2 for i in res])

def sum_days_team():
    team_overall = {}
    for day in team_data:
        for team in team_data[day]:
            if team == '':
                print("Empty team", day)
            if team not in team_overall:
                team_list.append(team)
                team_overall[team] = {'stars': [0,0,0,0,0], 'total_players': 0, 'weighted_strength': 0}
            team_overall[team]['stars'] = [team_overall[team]['stars'][i] + team_data[day][team]['stars'][i] for i in range(5)]
            team_overall[team]['total_players'] += team_data[day][team]['total_players']
            team_overall[team]['weighted_strength'] += team_data[day][team]['weighted_strength']
        for team in team_list:
            if team not in list(team_data[day].keys()):
                team_data[day][team] = {'stars': [0,0,0,0,0], 'total_players': 0, 'weighted_strength': 0}
        
    return team_overall


def find_zeroes(weights):
    out = scipy.optimize.fmin_l_bfgs_b(
          func=pen2, x0=[0.9, 0.9], args=(weights,), bounds=[(0.01,1), (0.01,1)], approx_grad=True, factr=1E8, iprint=-1)
    l1, l2 = float(out[0][0]), float(out[0][1])
    return l1,l2


def find_weights(init_weights, l1=.9, l2=1.):
    ad, ac = handicap_zeroes(l1,l2)
    bounds = [(0, None), (0, None), (0, None), (0, None), (1.0, 1.0)]
    out = scipy.optimize.fmin_l_bfgs_b(
        func=pen, x0=init_weights, bounds=bounds,args=(ad, ac, False), approx_grad=True, iprint=-1, factr=1E8, maxiter=1E+8, maxfun=1E+8)
    weights = [float(x) for x in list(out[0])]

    return weights

if __name__ == '__main__':
    for p in texas_players:
        texas_players[p]['days'] = sorted(texas_players[p]['days'])
        if texas_players[p]['stars'] >= 4 and 29 not in texas_players[p]['days']:
            print((p,texas_players[p]))
    _onestar_weights = [1,2,8,16,25]
    weights = [float(x)/_onestar_weights[-1] for x in _onestar_weights]
    l1,l2 = find_zeroes(weights)
    print("\nEstimated percentage of 0 multipliers:\n 1* %s%% 2* %s%%" % (round((1 - l1) * 100, 4), round((1 - l2) * 100, 4)))
    weights = find_weights(weights)
    print("\nWeights:")
    output_lst([round(x/weights[4], 3) for x in weights])

    print("\n1-normalized weights:")
    output_lst([round(x/weights[0], 2) for x in weights])

    strength = [weights[i] * all_stars[i] for i in range(5)]
    total = sum(strength)
    strength = [round(x / total, 2) for x in strength]
    print("\nRelative Star Strength:")
    output_lst(strength, True)
    for day in team_data:
        for team in team_data[day]:
            s = team_data[day][team]['stars']
            team_data[day][team]['weighted_strength'] = sum([s[i] * weights[i] for i in range(5)])
    team_overall = sum_days_team()
    print("\nTeam Stats")
    days = sorted(days_data.keys())
    fst, last = days[0],days[-1]
    team_stats, output, abd = {},{},{'Reds': {}, 'Allies':{}}
    alliance_stats = {a:{'Latest Strength':0, 'Latest Players':0} for a in ['Reds', 'Allies']}
    red_teams = ['Alabama', 'Nebraska', 'Ohio State', 'Oklahoma', 'Texas A&M', 'Wisconsin', 'Virginia Tech']
    blue_teams = ['Texas', 'Florida', 'Michigan', 'Georgia Tech', 'Clemson']
    for team in team_overall:
        latest_distro = [round(float(x)/sum(team_data[days[-1]][team]['stars']), 3) for x in team_data[days[-1]][team]['stars'] if sum(team_data[days[-1]][team]['stars']) != 0]
        strength_by_day = []
        growth_by_day = []
        players_by_day = []
        alliance = ''
        if team in red_teams:
            alliance = "Reds"
        if team in blue_teams:
            alliance = "Allies"
        last_day_strength = team_data[last][team]['weighted_strength']
        first_day_strength = team_data[fst][team]['weighted_strength'] 
        if alliance:
            alliance_stats[alliance]['Latest Strength'] += last_day_strength
            alliance_stats[alliance]['Latest Players'] += team_data[last][team]['total_players']

        for day in team_data:
            player_count = team_data[day][team]['total_players']
            players_by_day.append((day,player_count))
            day_strength = team_data[day][team]['weighted_strength']
            strength_by_day.append((day, round(day_strength,1)))              
            if day != fst:            
                yesterday_strength = team_data[day-1][team]['weighted_strength']
                growth = day_strength - yesterday_strength
                if last_day_strength != 0:
                    relative_growth = growth/day_strength
                else:
                    relative_growth = 0
                growth_by_day.append((day, round(growth,1), '{:.1%}'.format(round(relative_growth,3))))
            if alliance:
                if day not in abd[alliance]:
                    abd[alliance][day] = {'strength': 0, 'players':0}
                abd[alliance][day]['strength'] += day_strength
                abd[alliance][day]['players'] += player_count
        total_strength = round(team_overall[team]['weighted_strength'], 2)
        relative_to_tx = round(strength_by_day[-1][1]/team_data[last]['Texas']['weighted_strength'], 2)
        # star_dist_chage = sorted([[round(float(team_data[day][team]['stars'][x])/sum(team_data[day][team]['stars']) - float(team_data[days[0]][team]['stars'][x])/sum(team_data[days[0]][team]['stars']), 3) for x in range(5) if sum(team_data[day][team]['stars']) > 0] for day in team_data if sorted(list(team_data.keys())).index(day) != 0 ])
        per_capita_strength = round(team_overall[team]['weighted_strength']/team_overall[team]['total_players'], 2)          
        if relative_to_tx > 0:
            team_stats[team] = {
                # 'Latest day Star Distribution': str(latest_distro),
                'Daily Strength': str(strength_by_day[-7:]),
                'Daily Growth': str(growth_by_day[-7:]),
                'Strength compared to Texas': '{0:.0%}'.format(relative_to_tx),
                'Daily Players': str(players_by_day[-7:])
            }
    from json import encoder
    encoder.FLOAT_REPR = lambda o: format(o, '.2f')
    _red_str, _red_pl = alliance_stats['Reds']['Latest Strength'], float(alliance_stats['Reds']['Latest Players'])
    _blu_str, _blu_pl = alliance_stats['Allies']['Latest Strength'], float(alliance_stats['Allies']['Latest Players'])
    for a in abd:
        alliance_stats[a]['Strength by day'] = str([(d,round(abd[a][d]['strength'],1)) for d in abd[a]][-7:])
        alliance_stats[a]['Players by day'] = str([(d,abd[a][d]['players']) for d in abd[a]][-7:])
        alliance_stats[a]['Per capita'] = _red_str/_red_pl if a == 'Reds' else _blu_str/_blu_pl   
    alliance_stats['Reds']['Relative Strength'] = '{:.1%}'.format(_red_str/_blu_str)
    alliance_stats['Reds']['Relative Players'] = '{:.1%}'.format(_red_pl/_blu_pl)
    print(json.dumps(team_stats, indent=2, sort_keys=True))
    print(json.dumps(alliance_stats, indent=2, sort_keys=True))

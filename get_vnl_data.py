import requests
from bs4 import BeautifulSoup
import pandas as pd
import os

CURDIR = './'
TEAM_TO_ABBR = {'china': 'chn', 'belgium': 'bel', 'brazil': 'bra', 
                'bulgaria': 'bul', 'dominican republic': 'dom', 
                'germany': 'ger', 'italy': 'ita', 'japan': 'jpn', 
                'korea': 'kor', 'netherlands': 'ned', 'poland': 'pol', 
                'russia': 'rus',  'serbia': 'srb', 'thailand': 'tha',
                'turkey': 'tur', 'usa': 'usa'}


def format_snake(c):
    """
    Helper function for turning colnames into snake format
    """
    c_list = c.split(' ')
    # Change to lower case
    c_list = [w.lower() for w in c_list]
    return '_'.join(c_list)


def create_unique_strings(org_l):
    """
    Add prefix to the string if the strings in the the list are duplicates.
    """
    l = []
    for name in org_l:
        if name not in l:
            l.append(name)
            continue
        count = 0
        while  str(count) + '/' + name in l:
            count += 1
        l.append(str(count) + '/' + name)
    return l


def save_csv(df, filename):
    """
    Save the dataframe as a csv file.
    """
    fname = os.path.join(CURDIR, filename)
    df.to_csv(fname, index=False)
    print(fname + ' saved.')
    return True


def retrieve_first_table(url, table_idx=0, header_span=False, th_row=0, 
                         prefix_col=0, override_column=None, td_span=False):
  """
  Scrape the first table on the page at url.
  """
  data = requests.get(url).text
  soup = BeautifulSoup(data, "lxml")

  # Retrive table
  table = soup.find_all("table")[table_idx]
  
  # Find column names
  if override_column is None:
    header = table.thead.find_all('tr')[th_row].find_all('th')
    if header_span:
      colnames = [th.find_all('span')[0].text for th in header]
    else:
      colnames = [th.text for th in header]
    colnames = ['']*prefix_col + colnames
    # Change column names into snake format
    colnames = [format_snake(c) for c in colnames]
    # Make sure the column names are unique
    colnames = create_unique_strings(colnames)
  else:
    colnames = override_column
  
  df = pd.DataFrame(columns=colnames)

  # Collecte table data
  for tr in table.tbody.find_all('tr'):    
      # Find all data for each column
      columns = tr.find_all('td')
      if columns == []:
        continue
      if td_span:
        row_dict = {}
        for i in range(len(columns)):
          spans = columns[i].find_all('span')
          if spans:
            value = '-'.join([span.text.strip() for span in spans])
          else:
            value = columns[i].text.strip()
          row_dict[colnames[i]] = value
      else:
          row_dict = {colnames[i]: columns[i].text.strip() for i in range(len(columns))}
      df = df.append(row_dict, ignore_index=True)
  return df


def get_match_summary():
    """
    Get the match summary for the round robin.
    """
    match_summary_url = "https://en.volleyballworld.com/en/vnl/2019/women/resultsandranking/round1"
    colnames = ['number', 'date', 'teams', 'sets', 'set1_point', 'set2_point', 
                'set3_point', 'set4_point', 'set5_point', 
                'pionts', 'time', 'audience']
    match_summary_df = retrieve_first_table(match_summary_url, override_column=colnames, td_span=True, table_idx=1)
    for i in range(1, 6):
        # Clean the set point columns
        match_summary_df['set%s_point' % i] = match_summary_df['set%s_point' % i]\
            .apply(lambda x: (x[:2] if x[1].isnumeric() else x[0]) + '-' + 
                (x[-2:] if x[-2].isnumeric() else x[-1]) if x!='-' else x)
    return match_summary_df


def save_best_players():
    """
    Save 7 csv files for the best player data.
    """
    positions = ['best-scorers', 'best-spikers', 'best-blockers', 'best-servers', 'best-setters', 'best-diggers', 'best-receivers']
    base_url_best_players = "https://en.volleyballworld.com/en/vnl/2019/women/statistics/"

    for i in range(7):
        df = retrieve_first_table(base_url_best_players, table_idx=i, header_span=False)
        # Drop the last row
        print(df.tail(1))
        df.drop(df.tail(1).index,inplace=True)
        # Insert a rank column
        df['rank'] = list(range(1, len(df)+1))
        save_csv(df, positions[i] + '.csv')
        
    return df


def get_team_rank_with_match():
    """
    Save the team rank csv file.
    """
    # Scrape table from the webpage
    team_rank_match_url = 'https://en.volleyballworld.com/en/vnl/2019/women/resultsandranking/round1'
    team_rank_match_df = retrieve_first_table(team_rank_match_url, 
                                            header_span=False, th_row=1, prefix_col=3)
    # Drop empty column
    team_rank_match_df.drop(team_rank_match_df.columns[2], axis=1, inplace=True)

    # Set column names
    colnames = team_rank_match_df.columns
    suffix_replace_dict = {'0/': 'set_', '1/': 'point_'}
    for old in suffix_replace_dict:
        new = suffix_replace_dict[old]
        colnames = [name.replace(old, new) for name in colnames]

    # Rename columns
    colnames[:5] = ['rank', 'team_full', 'match_total', 'match_win', 'match_lose']
    colnames[-1] = 'point_ratio'
    colnames[-4] = 'set_ratio'
    team_rank_match_df.columns = colnames

    # Insert column for team abbreviation
    team_rank_match_df['team'] = team_rank_match_df['team_full'].apply(lambda x: TEAM_TO_ABBR[x.lower()].upper())

    return team_rank_match_df

def get_player_bio_df():
    """
    Save player bio into a csv file.
    """
    player_all_df = pd.DataFrame()
    for team in TEAM_TO_ABBR:
        abbr = TEAM_TO_ABBR[team]
        link_part = '%s-%s' % (abbr, team)
        player_url = "https://en.volleyballworld.com/en/vnl/2019/women/teams/%s/team_roster" % link_part
        player_df = retrieve_first_table(player_url, header_span=False)
        # Drop index
        player_df.drop(player_df.columns[0], axis=1, inplace=True)
        # Insert a team column
        player_df['team'] = abbr.upper()
        player_all_df = pd.concat([player_all_df, player_df])

    return player_all_df


def main():
    player_df = get_player_bio_df()
    team_rank_df = get_team_rank_with_match()
    save_csv(player_df, 'player_bio.csv')
    save_csv(team_rank_df, 'team_rank.csv')

    save_best_players()

    match_summary_df = get_match_summary()
    save_csv(match_summary_df, 'round_robin.csv')

if __name__ == '__main__':
    main()

import pandas as pd

## load the data sets

NIBRS = "/Users/adalimepowell/Desktop/WISWOM/WI-2024"

victim           = pd.read_csv(f"{NIBRS}/NIBRS_VICTIM.csv",
                               usecols=['victim_id', 'incident_id', 'sex_code',
                                        'age_num', 'race_id', 'victim_type_id'])
offense          = pd.read_csv(f"{NIBRS}/NIBRS_OFFENSE.csv",
                               usecols=['offense_id', 'incident_id', 'offense_code'])
offense_type     = pd.read_csv(f"{NIBRS}/NIBRS_OFFENSE_TYPE.csv",
                               usecols=['offense_code', 'offense_name'])
victim_offense   = pd.read_csv(f"{NIBRS}/NIBRS_VICTIM_OFFENSE.csv",
                               usecols=['victim_id', 'offense_id'])
victim_offender  = pd.read_csv(f"{NIBRS}/NIBRS_VICTIM_OFFENDER_REL.csv",
                               usecols=['victim_id', 'offender_id', 'relationship_id'])
relationship     = pd.read_csv(f"{NIBRS}/NIBRS_RELATIONSHIP.csv",
                               usecols=['relationship_id', 'relationship_code', 'relationship_name'])
offender         = pd.read_csv(f"{NIBRS}/NIBRS_OFFENDER.csv",
                               usecols=['offender_id', 'incident_id', 'sex_code',
                                        'age_num', 'race_id'])
incident         = pd.read_csv(f"{NIBRS}/NIBRS_incident.csv",
                               usecols=['incident_id', 'agency_id', 'incident_date'])
agencies         = pd.read_csv(f"{NIBRS}/agencies.csv",
                               usecols=['agency_id', 'county_name'])
race             = pd.read_csv(f"{NIBRS}/REF_RACE.csv",
                               usecols=['race_id', 'race_code', 'race_desc'])


# =============================================================================
# STEP 2 — REFERENCE CODES
# =============================================================================

# Relationship codes that constitute DV under FBI/NIBRS definition
dv_relationship_codes = ['SE', 'CS', 'XS', 'BG', 'CF', 'HR', 'PA', 'CH', 'SP', 'SC', 'FC', 'FP', 'ER']

# Offense codes that can constitute DV (Crimes Against Persons + Property)
# Group A offenses the FBI recognizes in a DV context
dv_offense_codes = [
    '09A', '09B', '09C',        # Murder/Nonneg Manslaughter, Neg Manslaughter, Justifiable Homicide
    '11A', '11B', '11C', '11D', # Rape, Sodomy, Sexual Assault w/ Object, Fondling
    '13A', '13B', '13C',        # Aggravated Assault, Simple Assault, Intimidation
    '210',                       # Extortion/Blackmail
    '220',                       # Burglary
    '23A', '23B', '23C', '23D', '23E', '23F', '23G', '23H',  # Larceny
    '240',                       # Motor Vehicle Theft
    '250',                       # Counterfeiting/Forgery
    '270',                       # Embezzlement
    '290',                       # Destruction/Damage/Vandalism
    '100',                       # Kidnapping/Abduction
    '120',                       # Robbery
]

# =============================================================================
# STEP 3 — FILTER TO DV VICTIMS
# =============================================================================

# Get victim_ids that had a DV relationship with their offender
dv_rel_victim_ids = victim_offender[
    victim_offender['relationship_id'].isin(
        relationship[relationship['relationship_code'].isin(dv_relationship_codes)]['relationship_id']
    )
]['victim_id']

# Get victim_ids that had a qualifying DV offense
dv_off_victim_ids = victim_offense[
    victim_offense['offense_id'].isin(
        offense[offense['offense_code'].isin(dv_offense_codes)]['offense_id']
    )
]['victim_id']

# A victim must meet BOTH criteria — right relationship AND qualifying offense
dv_victim_ids = set(dv_rel_victim_ids) & set(dv_off_victim_ids)

victim = victim[victim['victim_id'].isin(dv_victim_ids)].copy()

# =============================================================================
# STEP 4 — BASE JOINS  (1 row per victim)
# =============================================================================

# victim → race → incident → agencies
df = victim.merge(race, on='race_id', how='left')
df = df.merge(incident, on='incident_id', how='left')
df = df.merge(agencies, on='agency_id', how='left')

# =============================================================================
# STEP 5 — OFFENDERS  (pivot to offender_1 / offender_2, stay at 1 row per victim)
#
# victim_offender has one row per (victim, offender) pair.
# A victim can have multiple offenders.
# Strategy: number offenders 1..N per victim, pivot the first 2 into wide columns.
# offender_id comes from victim_offender — must do this BEFORE merging offender attrs.
# =============================================================================

# Attach relationship and offender attributes to each (victim, offender) pair
vo = (
    victim_offender
    .merge(relationship, on='relationship_id', how='left')
    .merge(
        offender.rename(columns={
            'sex_code': 'offender_sex',
            'age_num':  'offender_age',
            'race_id':  'offender_race_id',
        })[['offender_id', 'offender_sex', 'offender_age', 'offender_race_id']],
        on='offender_id', how='left',
    )
)

# Number each offender per victim (1, 2, 3, ...)
vo['offender_num'] = vo.groupby('victim_id').cumcount() + 1

# Pivot first 2 offenders into wide columns
vo_top2 = vo[vo['offender_num'] <= 2]
offender_pivot = vo_top2.pivot(
    index='victim_id',
    columns='offender_num',
    values=['offender_sex', 'offender_age', 'offender_race_id', 'relationship_code'],
)
# Flatten MultiIndex columns → offender_sex_1, offender_sex_2, relationship_code_1, ...
offender_pivot.columns = [f'{col}_{num}' for col, num in offender_pivot.columns]
offender_pivot = offender_pivot.reset_index()

df = df.merge(offender_pivot, on='victim_id', how='left')

# DV relationship flag: True if EITHER offender's relationship code is in dv_codes
df['is_dv_relationship'] = (
    df['relationship_code_1'].isin(dv_relationship_codes) |
    df['relationship_code_2'].isin(dv_relationship_codes)
)

# =============================================================================
# STEP 6 — OFFENSES  (fan out → 1 row per victim×offense)
#
# victim_offense is a bridge: one row per (victim, offense) pair.
# A victim can have multiple offenses, so this intentionally multiplies rows.
# Final grain: 1 row per victim×offense.
# =============================================================================

df = df.merge(victim_offense, on='victim_id', how='left')
df = df.merge(offense[['offense_id', 'offense_code']], on='offense_id', how='left')
df = df.merge(offense_type, on='offense_code', how='left')

# =============================================================================
# STEP 7 — INSPECT
# =============================================================================

print(df.shape)
print(df.dtypes)
print(df)

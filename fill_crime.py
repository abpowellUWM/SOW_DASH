import pandas as pd

NIBRS = ""

# Step 1 - load tables
victim = pd.read_csv(f"{NIBRS}/NIBRS_VICTIM.csv", usecols=['victim_id', 'incident_id', 'sex_code', 'age_num', 'race_id', 'victim_type_id'])
offense = pd.read_csv(f"{NIBRS}/NIBRS_OFFENSE.csv", usecols=['offense_id', 'incident_id', 'offense_code'])
offense_type = pd.read_csv(f"{NIBRS}/NIBRS_OFFENSE_TYPE.csv", usecols=['offense_code', 'offense_name'])
victim_offense = pd.read_csv(f"{NIBRS}/NIBRS_VICTIM_OFFENSE.csv", usecols=['victim_id', 'offense_id'])
victim_offender = pd.read_csv(f"{NIBRS}/NIBRS_VICTIM_OFFENDER_REL.csv", 
                               usecols=['victim_id', 'offender_id', 'relationship_id'])
offender = pd.read_csv(f"{NIBRS}/nibrs_offender.csv", usecols=['offender_id', 'incident_id', 'sex_code', 'age_num'])
incident = pd.read_csv(f"{NIBRS}/NIBRS_incident.csv", usecols=['incident_id', 'agency_id', 'incident_date'])
agencies = pd.read_csv(f"{NIBRS}/agencies.csv", usecols=['agency_id', 'county_name'])



# Step 2 - reference maps
race_map = {'W': 'White', 'B': 'Black or African American', 'A': 'Asian',
            'I': 'American Indian or Alaska Native',
            'P': 'Native Hawaiian or Other Pacific Islander', 'U': 'Unknown'}
age_bins   = [0, 17, 24, 34, 44, 54, 64, 200]
age_labels = ['Under 18', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']

# FBI UCR domestic relationship codes (Domestic Relationships and Violent Crimes, 2020-2024)
# SE=Spouse, CS=Common-Law Spouse, XS=Ex-Spouse, BG=Boyfriend/Girlfriend,
# CF=Child of Boyfriend/Girlfriend, HR=Homosexual Relationship, PA=Parent,
# CH=Child, SP=Stepparent, SC=Stepchild, FC=Foster Child, FP=Foster Parent, ER=Ex-Relationship
dv_codes = ['SE', 'CS', 'XS', 'BG', 'CF', 'HR', 'PA', 'CH', 'SP', 'SC', 'FC', 'FP', 'ER']

# FBI UCR violent crime offense codes
# 09A=Murder/Nonnegligent Manslaughter, 11A=Forcible Rape, 11B=Forcible Sodomy,
# 11C=Sexual Assault With Object, 11D=Forcible Fondling, 120=Robbery,
# 13A=Aggravated Assault, 13B=Simple Assault, 13C=Intimidation
violent_codes = ['09A', '11A', '11B', '11C', '11D', '120', '13A', '13B', '13C']
assault_codes = ['13A', '13B', '13C']

# Step 3 - join chain
df = victim.merge(incident, on='incident_id')
df = df.merge(agencies, on='agency_id')
df = df.merge(victim_offense, on='victim_id')
df = df.merge(offense, on='offense_id')
df = df.merge(offense_type, on='offense_code')

# Step 4 - filter individual victims and apply labels
df = df[df['victim_type_id'] == 4]
df['race'] = df['race_id'].map(race_map)
df['age_group'] = pd.cut(pd.to_numeric(df['age_num'], errors='coerce'), bins=age_bins, labels=age_labels)
df['race_clean'] = df['race'].str.lower().str.replace(' ', '_').str.replace('/', '_')



# Step 5 - assault aggregations
df_assault = df[df['offense_code'].isin(assault_codes)]

agg_sex   = df_assault.groupby(['county_name', 'sex_code']).size().reset_index(name='estimate')
agg_sex['var_base'] = agg_sex['sex_code'].map({'F': 'female_victims', 'M': 'male_victims', 'U': 'unknown_victims'})

agg_race  = df_assault.groupby(['county_name', 'sex_code', 'race_clean']).size().reset_index(name='estimate')
agg_race['var_base'] = agg_race['sex_code'].str.lower().map({'f': 'female', 'm': 'male', 'u': 'unknown'}) + '_victims_race_' + agg_race['race_clean']

agg_age   = df_assault.groupby(['county_name', 'sex_code', 'age_group']).size().reset_index(name='estimate')
agg_age['var_base'] = agg_age['sex_code'].str.lower().map({'f': 'female', 'm': 'male', 'u': 'unknown'}) + '_victims_age_' + agg_age['age_group'].astype(str).str.replace('-', '_')



# Step 6 - DV join and repeat flag
df_dv = (df[df['offense_code'].isin(violent_codes)]
         .merge(victim_offender, on='victim_id')
         .merge(offender.rename(columns={'sex_code': 'offender_sex'})[['offender_id', 'offender_sex']], on='offender_id', how='left'))
df_dv = df_dv[df_dv['relationship_id'].isin(dv_codes)]
df_dv['race_clean'] = df_dv['race'].str.lower().str.replace(' ', '_').str.replace('/', '_')

# Step 7 - DV aggregations
agg_dv_sex = df_dv.groupby(['county_name', 'sex_code']).size().reset_index(name='estimate')
agg_dv_sex['var_base'] = agg_dv_sex['sex_code'].map({'F': 'female_victims_dv', 'M': 'male_victims_dv', 'U': 'unknown_victims_dv'})

agg_dv_race = df_dv.groupby(['county_name', 'sex_code', 'race_clean']).size().reset_index(name='estimate')
agg_dv_race['var_base'] = agg_dv_race['sex_code'].str.lower().map({'f': 'female', 'm': 'male', 'u': 'unknown'}) + '_dv_race_' + agg_dv_race['race_clean']

agg_dv_age = df_dv.groupby(['county_name', 'sex_code', 'age_group']).size().reset_index(name='estimate')
agg_dv_age['var_base'] = agg_dv_age['sex_code'].str.lower().map({'f': 'female', 'm': 'male', 'u': 'unknown'}) + '_dv_age_' + agg_dv_age['age_group'].astype(str).str.replace('-', '_')

agg_dv_offender = df_dv.groupby(['county_name', 'offender_sex']).size().reset_index(name='estimate')
agg_dv_offender['var_base'] = 'dv_offender_' + agg_dv_offender['offender_sex'].str.lower()

# Step 8 - combine and format
final = pd.concat([
    agg_sex, agg_race, agg_age,
    agg_dv_sex,
    agg_dv_race, agg_dv_age,
    agg_dv_offender
])[['county_name', 'var_base', 'estimate']].reset_index(drop=True)

final = final.rename(columns={'county_name': 'county'})
final['geography_level'] = 'county'

final.to_csv(f"{NIBRS}/fact_crime_wi_county.csv", index=False)
print(final)


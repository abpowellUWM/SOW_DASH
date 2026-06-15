import pandas as pd


NIBRS = ""

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


dv_relationship_codes = ['SE', 'CS', 'XS', 'BG', 'CF', 'HR', 'PA', 'CH', 'SP', 'SC', 'FC', 'FP', 'ER']
dv_offense_codes = ['09A', '09B', '09C','11A', '11B', '11C', '11D','13A', '13B', '13C']

age_bins   = [0, 17, 24, 34, 44, 54, 64, 200]
age_labels = ['Under 18', '18-24', '25-34', '35-44', '45-54', '55-64', '65+']


county_lookup = (incident.merge(agencies, on='agency_id', how='left')
    [['incident_id', 'county_name']]
)

race_lookup = race[['race_id', 'race_desc']]


dv_rel_ids = set(relationship[relationship['relationship_code'].isin(dv_relationship_codes)]['relationship_id'])
dv_offense_ids = set(offense[offense['offense_code'].isin(dv_offense_codes)]['offense_id'])
victims_with_dv_rel = set(victim_offender[victim_offender['relationship_id'].isin(dv_rel_ids)]['victim_id'])
victims_with_dv_offense = set(victim_offense[victim_offense['offense_id'].isin(dv_offense_ids)]['victim_id'])
dv_victim_ids = victims_with_dv_rel & victims_with_dv_offense

victim_dv = victim[victim['victim_id'].isin(dv_victim_ids)].copy()
victim_dv = victim_dv.merge(race_lookup, on='race_id', how='left')
victim_dv = victim_dv.merge(county_lookup, on='incident_id', how='left')

victim_dv['age_group'] = (
    pd.cut(
        pd.to_numeric(victim_dv['age_num'], errors='coerce'),
        bins=age_bins, labels=age_labels, right=True, include_lowest=True,
    ).astype(str).replace('nan', None)
)


victim_count_rows = pd.DataFrame({
    'county':       victim_dv['county_name'].values,
    'metric':       'victim_count',
    'estimate':     1,
    'vic_sex':      victim_dv['sex_code'].values,
    'vic_race':     victim_dv['race_desc'].values,
    'vic_age':      victim_dv['age_group'].values,
    'off_sex':      None,
    'off_race':     None,
    'off_age':      None,
    'relationship': None,
})


dv_offender_ids = set(
    victim_offender[
        victim_offender['victim_id'].isin(dv_victim_ids) &
        victim_offender['relationship_id'].isin(dv_rel_ids)
    ]['offender_id']
)

offender_dv = offender[offender['offender_id'].isin(dv_offender_ids)].copy()
offender_dv = offender_dv.merge(race_lookup, on='race_id', how='left')
offender_dv = offender_dv.merge(county_lookup, on='incident_id', how='left')
offender_dv['age_group'] = (
    pd.cut(
        pd.to_numeric(offender_dv['age_num'], errors='coerce'),
        bins=age_bins, labels=age_labels, right=True, include_lowest=True,
    )
    .astype(str)
    .replace('nan', None)
)


offender_count_rows = pd.DataFrame({
    'county':       offender_dv['county_name'].values,
    'metric':       'offender_count',
    'estimate':     1,
    'vic_sex':      None,
    'vic_race':     None,
    'vic_age':      None,
    'off_sex':      offender_dv['sex_code'].values,
    'off_race':     offender_dv['race_desc'].values,
    'off_age':      offender_dv['age_group'].values,
    'relationship': None,
})

dv_vo = (
    victim_offense[
        victim_offense['victim_id'].isin(dv_victim_ids) &
        victim_offense['offense_id'].isin(dv_offense_ids)
    ]
    .merge(offense[['offense_id', 'offense_code']], on='offense_id', how='left')
    .merge(offense_type, on='offense_code', how='left')
)


dv_vo['metric'] = (
    'victim_'
    + dv_vo['offense_name']
      .str.lower()
      .str.replace(r'[^a-z0-9]+', '_', regex=True)
      .str.strip('_')
)

dv_vo_links = (
    victim_offender[
        victim_offender['victim_id'].isin(dv_victim_ids) &
        victim_offender['relationship_id'].isin(dv_rel_ids)
    ][['victim_id', 'offender_id', 'relationship_id']]
    # Add the plain-English relationship name (e.g. "Spouse", "Boyfriend/Girlfriend")
    .merge(relationship[['relationship_id', 'relationship_name']], on='relationship_id', how='left')
)

dv_offense_offender = dv_vo.merge(dv_vo_links, on='victim_id', how='left')

dv_offense_offender = dv_offense_offender.merge(
    victim_dv[['victim_id', 'county_name', 'sex_code', 'race_desc', 'age_group']],
    on='victim_id', how='left',
)

offender_demo = (
    offender_dv[['offender_id', 'sex_code', 'race_desc', 'age_group']]
    .drop_duplicates('offender_id')
    .rename(columns={'sex_code': 'off_sex', 'race_desc': 'off_race', 'age_group': 'off_age'})
)


dv_offense_offender = dv_offense_offender.merge(offender_demo, on='offender_id', how='left')

offense_type_rows = pd.DataFrame({
    'county':       dv_offense_offender['county_name'].values,
    'metric':       dv_offense_offender['metric'].values,
    'estimate':     1,
    'vic_sex':      dv_offense_offender['sex_code'].values,
    'vic_race':     dv_offense_offender['race_desc'].values,
    'vic_age':      dv_offense_offender['age_group'].values,
    'off_sex':      dv_offense_offender['off_sex'].values,
    'off_race':     dv_offense_offender['off_race'].values,
    'off_age':      dv_offense_offender['off_age'].values,
    'relationship': dv_offense_offender['relationship_name'].values,
})


fact_crime_flat = pd.concat(
    [victim_count_rows, offender_count_rows, offense_type_rows],
    ignore_index=True,
)[['county', 'metric', 'estimate', 'vic_sex', 'vic_race', 'vic_age',
   'off_sex', 'off_race', 'off_age', 'relationship']]


fact_crime_agg = (
    fact_crime_flat
    .groupby(
        ['county', 'metric', 'vic_sex', 'vic_race', 'vic_age',
         'off_sex', 'off_race', 'off_age', 'relationship'],
        dropna=False   # keep rows where some columns are None (count/offender rows)
    )
    .agg(estimate=('estimate', 'sum'))
    .reset_index()
)

print(f"Aggregated: {fact_crime_agg.shape[0]:,} rows x {fact_crime_agg.shape[1]} columns")
print()
print(fact_crime_agg.head(20))
print()
print("Metrics present:")
print(fact_crime_agg.groupby('metric')['estimate'].sum())

# Save the aggregated table to a CSV file in the same folder as the raw data
fact_crime_agg.to_csv(f"{NIBRS}/fact_crime_agg.csv", index=False)
print(f"\nSaved to {NIBRS}/fact_crime_agg.csv")















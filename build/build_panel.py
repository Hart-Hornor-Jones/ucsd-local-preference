"""Build the school x period panel behind the UCSD local-preference visualizer.
Sources: the 2026-09-29 analysis folder (panel_ucsd_local_with_covariates.csv, school_year_predictions.csv),
the ca-hs-proficiency panel (CAASPP/STAR/CAHSEE), CDE enrollment, CDE school coordinates.
Periods: fall 1994-2025 singly, plus seven pooled eras stored at pseudo-years 2026-2032."""
import pandas as pd, numpy as np, json, os
A="../../UCSD Local Preference 2026-09-29/"
ERAS=[(2026,'A',1994,1996,'residency points'),(2027,'B',1997,1998,'residency as a qualitative factor'),
      (2028,'C',1999,2004,'Local 4% Plan'),(2029,'D',2005,2010,'after the BOARS ruling'),
      (2030,'E',2011,2017,'holistic review, no local tilt'),(2031,'F',2018,2021,'undocumented local advantage'),
      (2032,'G',2022,2025,'re-targeted, then fading')]
P=pd.read_csv(A+'panel_ucsd_local_with_covariates.csv',dtype={'ceeb':str,'cds14':str})
S=pd.read_csv(A+'school_year_predictions.csv',dtype={'ceeb':str,'cds14':str})[['ceeb','year','pred_adm_gpa','pred_adm_oth']]
P=P.merge(S,on=['ceeb','year'],how='left')
P=P[P.sd_app>0].copy()
# proficiency measures from the published panel
pl=pd.read_csv('../../ca-hs-proficiency/data/panel_long.csv',dtype={'cds14':str})
pl=pl[pl.measure.isin(['caaspp','star','cahsee'])].pivot_table(index=['cds14','year'],columns='measure',values='value').reset_index()
P=P.drop(columns=[c for c in ['cahsee','star'] if c in P.columns]).merge(pl,on=['cds14','year'],how='left')
# coordinates -> distance
loc=pd.read_csv('../../uc-merit-admissions/data/components/school_locations.csv',dtype={'cds14':str})
P=P.merge(loc,on='cds14',how='left')
upp=pa0=pd.read_csv('../../uc-merit-admissions/data/panel_all9_by_year.csv',dtype={'ceeb':str}); upp=upp[upp.campus=='San Diego'][['ceeb','year','upp_pct']]
P=P.merge(upp,on=['ceeb','year'],how='left')
la1,lo1=np.radians(32.8801),np.radians(-117.2340)
la2,lo2=np.radians(P.latitude),np.radians(P.longitude)
P['dist']=3958.8*2*np.arcsin(np.sqrt(np.sin((la2-la1)/2)**2+np.cos(la1)*np.cos(la2)*np.sin((lo2-lo1)/2)**2))
# district names
dn=pd.read_csv('../../../hs data/race_ethnicity/cde_high_school_race_ethnicity_school_1981_2026.csv',dtype=str,usecols=['cds_code','district_name','academic_start_year'])
dn=dn[dn.academic_start_year=='2019'].drop_duplicates('cds_code'); dn['district']=dn.cds_code.str[:7]
dmap=dn.drop_duplicates('district').set_index('district').district_name
P['district']=P.cds14.str[:7]; P['district_name']=P.district.map(dmap)
# proficiency tercile (2015-19 CAASPP, statewide cuts)
pa=pd.read_csv('../../uc-merit-admissions/data/panel_all9_by_year.csv',dtype={'ceeb':str})
s=pa[(pa.campus=='San Diego')&pa.year.between(2015,2019)].groupby('ceeb').avg_pct_met.mean().dropna()
terc=pd.qcut(s,3,labels=[0,1,2]).astype(float).rename('prof_terc').reset_index()
P=P.merge(terc,on='ceeb',how='left')
# per-year derived
P['ucsd_admit']=100*P.sd_adm/P.sd_app
P['ucsd_yield']=100*P.sd_enr/P.sd_adm
P['ucsd_exp']=100*P.pred_adm_gpa/P.sd_app
P['ucsd_adv']=P.ucsd_admit-P.ucsd_exp
P['ucsd_exp2']=100*P.pred_adm_oth/P.sd_app
P['ucsd_adv2']=P.ucsd_admit-P.ucsd_exp2
P['oth_admit']=100*P.oth_adm/P.oth_app
P['ucsd_share']=100*P.ucsd_share_of_uc_apps
P['apps_per100']=(100*P.apps_per_senior).replace([np.inf,-np.inf],np.nan)
P['gpa_prem']=P.sd_adm_gpa-P.sd_app_gpa
P['urg_pct']=100*P.urg_share
P['lcff']=(P.upp_pct>75).astype(float); P.loc[P.upp_pct.isna(),'lcff']=np.nan
P['apps_per_quota']=(P.sd_app/P.quota).replace([np.inf,-np.inf],np.nan)
P['quota_bind']=((P.quota-P.pred_adm_gpa)>0).astype(float); P.loc[P.quota.isna()|P.pred_adm_gpa.isna(),'quota_bind']=np.nan
P.loc[P.local==0,['quota','apps_per_quota','quota_bind']]=np.nan
# ---- school list ----
first=P.sort_values('year').groupby('ceeb').agg(school_name=('school_name','last'),city=('city','last'),county=('county','last'),cds14=('cds14','last'),district=('district','last'),district_name=('district_name','last'),local=('local','max'),dist=('dist','first'),prof_terc=('prof_terc','first'),apps_mean=('sd_app','mean'),g12=('g12_own','mean')).reset_index()
def dgroup(r):
    if r.local!=1: return 5
    if r.district=='3768411': return 0
    if r.district=='3768338': return 1
    if r.county=='Imperial': return 2
    if r.district in ('3768296','3768346','3768213'): return 3
    return 4
first['dgroup']=first.apply(dgroup,axis=1)
CNTY=['San Diego','Imperial','Orange','Riverside','Los Angeles']
first['county_cat']=first.county.apply(lambda c: CNTY.index(c) if c in CNTY else 5)
first['dband']=pd.cut(first.dist,[-1,10,20,30,60,100,10000],labels=[0,1,2,3,4,5]).astype(float)
bind=P[(P.year.between(1999,2004))].groupby('ceeb').quota_bind.sum(min_count=1).rename('bind_years').reset_index()
first=first.merge(bind,on='ceeb',how='left'); first.loc[first.local==0,'bind_years']=np.nan
first['name']=first.school_name.str.title().str.replace(' High School',' High',regex=False)+' ('+first.city.str.title()+')'
first=first.sort_values(['local','county','name'],ascending=[False,True,True]).reset_index(drop=True)
idx={c:i for i,c in enumerate(first.ceeb)}
first.to_csv('../data/schools.csv',index=False)
# ---- measures ----
YEARLY={ # id: (column, dec, kind) kind: rate=ratio of sums for eras (num,den) ; wmean (weight col) ; mean
 'ucsd_admit':('ucsd_admit',1,('sd_adm','sd_app')),
 'ucsd_exp':('ucsd_exp',1,('pred_adm_gpa','sd_app')),
 'ucsd_adv':('ucsd_adv',1,'adv'),
 'ucsd_exp2':('ucsd_exp2',1,('pred_adm_oth','sd_app')),
 'ucsd_adv2':('ucsd_adv2',1,'adv2'),
 'ucsd_yield':('ucsd_yield',1,('sd_enr','sd_adm')),
 'ucsd_apps':('sd_app',0,'sum'),
 'ucsd_adm':('sd_adm',0,'sum'),
 'ucsd_app_gpa':('sd_app_gpa',2,'sd_app'),
 'ucsd_adm_gpa':('sd_adm_gpa',2,'sd_adm'),
 'gpa_prem':('gpa_prem',2,'sd_adm'),
 'uc_app_gpa':('uw_gpa',2,'uw_app'),
 'oth_admit':('oth_admit',1,('oth_adm','oth_app')),
 'ucsd_share':('ucsd_share',1,'sd_app'),
 'apps_per100':('apps_per100',1,'g12_own'),
 'caaspp':('caaspp',1,'mean'),'star':('star',1,'mean'),'cahsee':('cahsee',1,'mean'),
 'ctx_upp':('upp_pct',1,'mean'),'ctx_lcff':('lcff',0,'mean'),'ctx_urg':('urg_pct',1,'mean'),
 'quota':('quota',1,'sum'),'apps_per_quota':('apps_per_quota',2,('sd_app','quota')),'quota_bind':('quota_bind',0,'mean'),
}
CONST={'dist':('dist',1),'local':('local',0),'county_cat':('county_cat',0),'dgroup':('dgroup',0),'dband':('dband',0),'prof_terc':('prof_terc',0),'bind_years':('bind_years',0),'ctx_size':('g12',0)}
def row_string(vals,dec):
    sc=10**dec; return ','.join('' if (v is None or (isinstance(v,float) and not np.isfinite(v))) else str(int(round(v*sc))) for v in vals)
m={}
years=list(range(1994,2026))
for mid,(col,dec,kind) in YEARLY.items():
    rows=[]
    for y in years:
        d=P[P.year==y].set_index('ceeb')[col]
        vals=[d.get(c,np.nan) for c in first.ceeb]; rows.append(row_string(vals,dec))
    for (py,code,a,b,lab) in ERAS:
        e=P[P.year.between(a,b)]
        if kind=='adv':
            g=e.groupby('ceeb').agg(a=('sd_adm','sum'),p=('pred_adm_gpa','sum'),n=('sd_app','sum')); v=100*(g.a-g.p)/g.n
        elif kind=='adv2':
            g=e.groupby('ceeb').agg(a=('sd_adm','sum'),p=('pred_adm_oth','sum'),n=('sd_app','sum')); v=100*(g.a-g.p)/g.n
        elif isinstance(kind,tuple):
            ee=e[e[kind[0]].notna()&e[kind[1]].notna()]; g=ee.groupby('ceeb').agg(a=(kind[0],'sum'),b=(kind[1],'sum')); v=g.a/g.b
            if mid in ('ucsd_admit','ucsd_exp','ucsd_exp2','ucsd_yield','oth_admit'): v=100*v
        elif kind=='sum': v=e.groupby('ceeb')[col].sum(min_count=1)
        elif kind=='mean': v=e.groupby('ceeb')[col].mean()
        else:
            ee=e[e[col].notna()&e[kind].notna()&(e[kind]>0)]; v=(ee[col]*ee[kind]).groupby(ee.ceeb).sum()/ee.groupby('ceeb')[kind].sum()
        v=v.replace([np.inf,-np.inf],np.nan)
        vals=[v.get(c,np.nan) for c in first.ceeb]; rows.append(row_string(vals,dec))
    m[mid]={'y0':1994,'y1':2032,'dec':dec,'rows':rows}
for mid,(col,dec) in CONST.items():
    m[mid]={'y0':1994,'y1':2032,'dec':dec,'k':1,'rows':[row_string(first[col].tolist(),dec)]}
PANEL={'names':first.name.tolist(),'ceeb':first.ceeb.tolist(),'sizes':[int(round(v)) for v in first.apps_mean.fillna(1)],'m':m}
json.dump(PANEL,open('panel_blob.json','w'),separators=(',',':'))
# long CSV for the repo
L=[]
for mid in list(YEARLY)+list(CONST):
    pm=m[mid]; sc=10**pm['dec']
    for r_i,row in enumerate(pm['rows']):
        y='const' if pm.get('k') else (1994+r_i if 1994+r_i<=2025 else 'era_'+ERAS[1994+r_i-2026][1])
        for c_i,v in enumerate(row.split(',')):
            if v!='': L.append((first.ceeb[c_i],y,mid,int(v)/sc))
pd.DataFrame(L,columns=['ceeb','period','measure','value']).to_csv('../data/panel_long.csv',index=False)
print(len(first),'schools;', (first.local==1).sum(),'local;', len(L),'long rows'); print(first.dgroup.value_counts().sort_index().to_dict(), first.county_cat.value_counts().sort_index().to_dict())

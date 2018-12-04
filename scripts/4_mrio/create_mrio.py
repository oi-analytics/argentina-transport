# -*- coding: utf-8 -*-
"""
Created on Fri Nov 30 13:16:48 2018

@author: cenv0574
"""

import os
import pandas as pd
import numpy as np
import oia.utils
from ras_method import ras_method
import subprocess

import warnings
warnings.filterwarnings('ignore')

data_path= oia.utils.load_config()['paths']['data']

def est_trade_value(x,output_new,sector):
    if sector is not 'other':
        sec_output = output_new.sum(axis=1).loc[output_new.sum(axis=1).index.get_level_values(1) == sector].reset_index()
    else:
        sec_output = output_new.sum(axis=1).loc[output_new.sum(axis=1).index.get_level_values(1) == 'VA'].reset_index()
        
    x['gdp'] = x.gdp*min(sec_output.loc[sec_output.region==x.reg1].values[0][2],sec_output.loc[sec_output.region==x.reg2].values[0][2])
#    x['gdp'] = x.gdp*(sec_output.loc[sec_output.region==x.reg1].values[0][2])
    return x

def indind_iotable(sup_table,use_table,sectors):
    # GET VARIABLES
    x = np.array(sup_table.sum(axis=0)) # total production on industry level
    g = np.array(sup_table.sum(axis=1)) # total production on product level
    F = use_table.iloc[:16,16:].sum(axis=1)
    
    #Numpify
    Sup_array = np.asarray(sup_table.iloc[:len(sectors),:len(sectors)]) # numpy array if supply matrix
    Use_array = np.asarray(use_table.iloc[:len(sectors),:len(sectors)]) # numpy array of use matrix
    
    g_diag_inv = np.linalg.inv(np.diag(g)) # inverse of g (and diagolinized)
    x_diag_inv = np.linalg.inv(np.diag(x)) # inverse of x (and diagolinized)
    
    # Calculate the matrices
    B = np.dot(Use_array,x_diag_inv) # B matrix (U*x^-1)
    D = np.dot(Sup_array.T,g_diag_inv) # D matrix (V*g^-1)
    I_i = np.identity((len(x))) # Identity matrix for industry-to-industry
    
    # Inverse for industry-to-industry
    A_ii = np.dot(D,B)
    F_ii = np.dot(D,F)/1e6
    IDB_inv = np.linalg.inv((I_i-np.dot(D,B))) # (I-DB)^-1 
    
    # And canclulate sum of industries
    ind = np.dot(IDB_inv,np.dot(D,F)/1e6) # (I-DB)^-1 * DF
    
    IO = pd.concat([pd.DataFrame(np.dot(A_ii,np.diag(ind))),pd.DataFrame(F_ii)],axis=1)
    IO.columns = list(use_table.columns[:17])
    IO.index = list(use_table.columns[:16])
    VA = np.array(list(ind)+[0])-np.array(IO.sum(axis=0))
    VA[-1] = 0
    IO.loc['ValueA'] = VA
    
    return IO,VA

# =============================================================================
# # Load mapper functions to aggregate tables
# =============================================================================
ind_mapper = pd.read_excel(os.path.join(data_path,'economic_IO_tables','input','sh_cou_06_16.xls'),
                          sheet_name='ind_mapper',header=None)
ind_mapper = dict(zip(ind_mapper[0],ind_mapper[1]))

com_mapper = pd.read_excel(os.path.join(data_path,'economic_IO_tables','input','sh_cou_06_16.xls'),
                          sheet_name='com_mapper',header=None)
com_mapper = dict(zip(com_mapper[0],['P_'+x for x in com_mapper[1]]))

reg_mapper = pd.read_excel(os.path.join(data_path,'economic_IO_tables','input','sh_cou_06_16.xls'),
                          sheet_name='reg_mapper',header=None)
reg_mapper = dict(zip(reg_mapper[0], reg_mapper[1]))

sectors = [chr(i) for i in range(ord('A'),ord('P')+1)]

# =============================================================================
# Load supply table and aggregate 
# =============================================================================
sup_table_in = pd.read_excel(os.path.join(data_path,'economic_IO_tables','input','sh_cou_06_16.xls'),
                          sheet_name='Mat Oferta pb',skiprows=2,header=[0,1],index_col=[0,1],nrows=271)
sup_table_in = sup_table_in.drop('Total',level=0,axis=1)
sup_table = sup_table_in.copy()

sup_table.columns = sup_table.columns.get_level_values(0)
sup_table.columns = sup_table.columns.map(ind_mapper)
sup_table = sup_table.T.groupby(level=0,axis=0).sum()
sup_table.columns = sup_table.columns.get_level_values(0)
sup_table.columns = sup_table.columns.map(com_mapper)
sup_table = sup_table.T.groupby(level=0,axis=0).sum()

# =============================================================================
# Load use table and aggregate 
# =============================================================================
use_table = pd.read_excel(os.path.join(data_path,'economic_IO_tables','input','sh_cou_06_16.xls'),
                          sheet_name='Mat Utilizacion pc',skiprows=2,header=[0,1],index_col=[0,1],nrows=271)

basic_prod_prices = use_table[['IMPORTACIONES  (CIF a nivel de producto y FOB a nivel total)',
                               'AJUSTE CIF/FOB DE LAS IMPORTACIONES','DERECHOS DE IMPORTACION',
                               'IMPUESTOS A LOS PRODUCTOS NETOS DE SUBSIDIOS','MARGENES DE COMERCIO',
                               'MARGENES DE TRANSPORTE','IMPUESTO AL VALOR AGREGADO NO DEDUCIBLE',
                                ]]*-1

use_table = use_table.drop(['PRODUCCION NACIONAL A PRECIOS BASICOS',
                            'IMPORTACIONES  (CIF a nivel de producto y FOB a nivel total)',
                            'AJUSTE CIF/FOB DE LAS IMPORTACIONES','DERECHOS DE IMPORTACION',
                            'IMPUESTOS A LOS PRODUCTOS NETOS DE SUBSIDIOS','MARGENES DE COMERCIO',
                            'MARGENES DE TRANSPORTE','IMPUESTO AL VALOR AGREGADO NO DEDUCIBLE',
                            'OFERTA TOTAL A PRECIOS DE  COMPRADOR','UTILIZACION INTERMEDIA',
                            'UTILIZACION FINAL','DEMANDA TOTAL'],level=0,axis=1)

basic_prod_prices.columns = basic_prod_prices.columns.get_level_values(0)
basic_prod_prices = basic_prod_prices.T.groupby(level=0,axis=0).sum()
basic_prod_prices.columns = basic_prod_prices.columns.get_level_values(0)
basic_prod_prices.columns = basic_prod_prices.columns.map(com_mapper)
basic_prod_prices = basic_prod_prices.T.groupby(level=0,axis=0).sum()
basic_prod_prices = basic_prod_prices.astype(int)

use_table.columns = use_table.columns.get_level_values(0)
use_table.columns = use_table.columns.map(ind_mapper)
use_table = use_table.T.groupby(level=0,axis=0).sum()
use_table.columns = use_table.columns.get_level_values(0)
use_table.columns = use_table.columns.map(com_mapper)
use_table = use_table.T.groupby(level=0,axis=0).sum()

use_table= pd.concat([use_table,basic_prod_prices],axis=1)

# =============================================================================
# Create IO table and translate to 2016 values
# =============================================================================
IO_ARG,VA = indind_iotable(sup_table,use_table,sectors)

va_new = [498.319,21.986,264.674,1113.747,123.094,315.363,1076.121,168.899,441.293,321.376,750.356,647.929,448.372,426.642,235.624,58.837]
u = ((((np.array(IO_ARG.sum(axis=0)))/VA)[:16])*va_new)
new_fd = (np.array(IO_ARG.iloc[:,16]/(np.array(IO_ARG.sum(axis=0))))*np.array(list(u)+[0]))
new_IO = ras_method(np.array(IO_ARG)[:16,:17],np.array((u)),np.array(list(u-np.array(va_new))+[sum(va_new)]), eps=1e-5)
NEW_IO = pd.DataFrame(new_IO,columns=sectors+['FD'],index=sectors)
NEW_IO.loc['ValueA'] = np.array(list(va_new)+[0])

# =============================================================================
# Save 2016 table and the indices to prepare disaggregation
# =============================================================================

NEW_IO.to_csv(os.path.join(data_path,'mrio_analysis','basetable.csv'),index=False,header=False)
pd.DataFrame([len(sectors+['other1'])*['ARG'],sectors+['other']]).T.to_csv(os.path.join(data_path,'mrio_analysis','indices.csv'),index=False,header=False)


''' First iteration, no trade to determine total regional input and output '''

# =============================================================================
# Load provincial data
# =============================================================================

prov_data = pd.read_excel(os.path.join(data_path,'economic_IO_tables','input','PIB_provincial_06_17.xls'),sheet_name='VBP',
                         skiprows=3,index_col=[0],header=[0],nrows=71)
prov_data = prov_data.loc[[x.isupper() for x in prov_data.index],:]
prov_data.columns = ['Ciudad de Buenos Aires', 'Buenos Aires', 'Catamarca', 'Cordoba',
       'Corrientes', 'Chaco', 'Chubut', 'Entre Rios', 'Formosa', 'Jujuy',
       'La Pampa', 'La Rioja', 'Mendoza', 'Misiones', 'Neuquen', 'Rio Negro',
       'Salta', 'San Juan', 'San Luis', 'Santa Cruz', 'Santa Fe',
       'Santiago del Estero', 'Tucuman', 'Tierra del Fuego',
       'No distribuido', 'Total']
region_names = list(prov_data.columns)[:-2]

prov_data.index = sectors+['TOTAL']


# =============================================================================
# Create proxy data for first iteration
# =============================================================================

# proxy level 2
proxy_reg_arg = pd.DataFrame(prov_data.iloc[-1,:24]/prov_data.iloc[-1,:24].sum()).reset_index()
proxy_reg_arg['year'] = 2016
proxy_reg_arg = proxy_reg_arg[['year','index','TOTAL']]
proxy_reg_arg.columns = ['year','id','gdp']
proxy_reg_arg.to_csv(os.path.join(data_path,'mrio_analysis','proxy_reg_arg.csv'),index=False)


# proxy level 4
for iter_,sector in enumerate(sectors+['other']):
    if sector is not 'other':
        proxy_sector = pd.DataFrame(prov_data.iloc[iter_,:24]/prov_data.iloc[iter_,:24].sum()).reset_index()
        proxy_sector['year'] = 2016
        proxy_sector['sector'] = 'sec{}'.format(sector)
        proxy_sector = proxy_sector[['year','sector','index',sector]]
        proxy_sector.columns = ['year','sector','region','gdp']
        proxy_sector.to_csv(os.path.join(data_path,'mrio_analysis','proxy_sec{}.csv'.format(sector)),index=False)
    else:
        proxy_sector = pd.DataFrame(prov_data.iloc[-1,:24]/prov_data.iloc[-1,:24].sum()).reset_index()
        proxy_sector['year'] = 2016
        proxy_sector['sector'] = sector+'1'
        proxy_sector = proxy_sector[['year','sector','index','TOTAL']]
        proxy_sector.columns = ['year','sector','region','gdp']
        proxy_sector.to_csv(os.path.join(data_path,'mrio_analysis','proxy_{}.csv'.format(sector)),index=False)
        
# proxy level 18
mi_index = pd.MultiIndex.from_product([sectors+['other'], region_names, sectors+['other'], region_names],
                                     names=['sec1', 'reg1','sec2','reg2'])
for iter_,sector in enumerate(sectors+['other']):
    if sector is not 'other':
        proxy_trade = pd.DataFrame(columns=['year','gdp'],index= mi_index).reset_index()
        proxy_trade['year'] = 2016
        proxy_trade['gdp'] = 0
        proxy_trade = proxy_trade.query("reg1 != reg2")
        proxy_trade = proxy_trade.loc[proxy_trade.sec1 == sector]
        proxy_trade['sec1'] = ['sec'+x if x is not 'other' else 'other' for x in proxy_trade.sec1 ]
        proxy_trade['sec2'] = ['sec'+x if x is not 'other' else 'other' for x in proxy_trade.sec2 ]
        proxy_trade = proxy_trade[['year','sec1','reg1','sec2','reg2','gdp']]
        proxy_trade.columns = ['year','sector','region','sector','region','gdp']
        proxy_trade.to_csv(os.path.join(data_path,'mrio_analysis','proxy_trade_sec{}.csv'.format(sector)),index=False)    
    else:
        proxy_trade = pd.DataFrame(columns=['year','gdp'],index= mi_index).reset_index()
        proxy_trade['year'] = 2016
        proxy_trade['gdp'] = 0
        proxy_trade = proxy_trade.query("reg1 != reg2")    
        proxy_trade = proxy_trade.loc[proxy_trade.sec1 == sector]
        proxy_trade['sec1'] = ['sec'+x if x is not 'other' else 'other' for x in proxy_trade.sec1 ]
        proxy_trade['sec2'] = ['sec'+x if x is not 'other' else 'other' for x in proxy_trade.sec2 ]
        proxy_trade = proxy_trade[['year','sec1','reg1','sec2','reg2','gdp']]
        proxy_trade.columns = ['year','sector','region','sector','region','gdp']
        proxy_trade.to_csv(os.path.join(data_path,'mrio_analysis','proxy_trade_{}.csv'.format(sector)),index=False)
        
        
# =============================================================================
# Create first version of MRIO for Argentina
# =============================================================================

p = subprocess.Popen(['mrio_disaggregate', 'settings_notrade.yml'],
                     cwd=os.path.join(data_path, 'mrio_analysis'))
p.wait()

region_names_list = [item for sublist in [[x]*(len(sectors)+1) for x in region_names]
                     for item in sublist]

rows = ([x for x in sectors+['VA']])*len(region_names)
cols = ([x for x in sectors+['FD']])*len(region_names)

index_mi = pd.MultiIndex.from_arrays([region_names_list, rows], names=('region', 'row'))
column_mi = pd.MultiIndex.from_arrays([region_names_list, cols], names=('region', 'col'))

MRIO = pd.read_csv(os.path.join(data_path,'mrio_analysis','output1.csv'),header=None,index_col=None)
MRIO.index = index_mi
MRIO.columns = column_mi

# create predefined index and col, which is easier to read
sector_only = [x for x in sectors]*len(region_names)
col_only = ['FD']*len(region_names)

region_col = [item for sublist in [[x]*len(sectors) for x in region_names] for item in sublist] + \
    [item for sublist in [[x]*1 for x in region_names] for item in sublist]

column_mi_reorder = pd.MultiIndex.from_arrays(
    [region_col, sector_only+col_only], names=('region', 'col'))

# sum va and imports
valueA = MRIO.loc[MRIO.index.get_level_values(1) == 'VA'].sum(axis='index')

output_new = pd.concat([MRIO.loc[~MRIO.index.get_level_values(1).isin(['FD'])]])
output_new = output_new.reindex(column_mi_reorder, axis='columns')

''' Second iteration, including trade'''

# =============================================================================
# Load OD Matrix
# =============================================================================

od_matrix_total = pd.DataFrame(pd.read_excel(os.path.join(data_path,'OD_data','province_ods.xlsx'),
                          sheet_name='total',index_col=[0,1])).unstack(1).fillna(0)
od_matrix_total.columns.set_levels(['A','G','C','D','B','I'],level=0,inplace=True)
od_matrix_total.index = od_matrix_total.index.map(reg_mapper)
od_matrix_total = od_matrix_total.stack(0)
od_matrix_total.columns = od_matrix_total.columns.map(reg_mapper)
od_matrix_total = od_matrix_total.swaplevel(i=-2, j=-1, axis=0)


# =============================================================================
# Create proxy data for second iteration
# =============================================================================
# proxy level 14 
mi_index = pd.MultiIndex.from_product([sectors+['other'], region_names, region_names],
                                     names=['sec1', 'reg1','reg2'])

for iter_,sector in enumerate(sectors+['other']):
    if sector in ['A','G','C','D','B','I']:
        proxy_trade = (od_matrix_total.loc[sector]/od_matrix_total.loc[sector].sum(axis=0)).stack(0).reset_index()
        proxy_trade.columns = ['reg1','reg2','gdp']
        proxy_trade['year'] = 2016
        proxy_trade = proxy_trade.apply(lambda x: est_trade_value(x,output_new,sector),axis=1)
        proxy_trade['sec1'] = 'sec{}'.format(sector)
        proxy_trade = proxy_trade[['year','sec1','reg1','reg2','gdp']]
        proxy_trade.columns = ['year','sector','region','region','gdp']
        proxy_trade.to_csv(os.path.join(data_path,'mrio_analysis','proxy_trade14_sec{}.csv'.format(sector)),index=False)
    elif (sector is not 'other') & (sector not in ['A','G','C','D','B','I']): # &  (sector not in ['L','M','N','O','P']):
        proxy_trade = (od_matrix_total.sum(level=1)/od_matrix_total.sum(level=1).sum(axis=0)).stack(0).reset_index()
        proxy_trade.columns = ['reg1','reg2','gdp']
        proxy_trade['year'] = 2016
        proxy_trade = proxy_trade.apply(lambda x: est_trade_value(x,output_new,sector),axis=1)
        proxy_trade['sec1'] = 'sec{}'.format(sector)
        proxy_trade = proxy_trade[['year','sec1','reg1','reg2','gdp']]
        proxy_trade.columns = ['year','sector','region','region','gdp']
        proxy_trade.to_csv(os.path.join(data_path,'mrio_analysis','proxy_trade14_sec{}.csv'.format(sector)),index=False)

    else:
        proxy_trade = (od_matrix_total.sum(level=1)/od_matrix_total.sum(level=1).sum(axis=0)).stack(0).reset_index()
        proxy_trade.columns = ['reg1','reg2','gdp']
        proxy_trade['year'] = 2016
        proxy_trade = proxy_trade.apply(lambda x: est_trade_value(x,output_new,sector),axis=1)
        proxy_trade['sec1'] = sector+'1'
        proxy_trade = proxy_trade[['year','sec1','reg1','reg2','gdp']]
        proxy_trade.columns = ['year','sector','region','region','gdp']
        proxy_trade.to_csv(os.path.join(data_path,'mrio_analysis','proxy_trade14_{}.csv'.format(sector)),index=False)       
        
# proxy level 18
mi_index = pd.MultiIndex.from_product([sectors+['other'], region_names, sectors+['other'], region_names],
                                     names=['sec1', 'reg1','sec2','reg2'])
for iter_,sector in enumerate(sectors+['other']):
    if sector is not 'other':
        proxy_trade = pd.DataFrame(columns=['year','gdp'],index= mi_index).reset_index()
        proxy_trade['year'] = 2016
        proxy_trade['gdp'] = 0
        proxy_trade = proxy_trade.query("reg1 != reg2")
        proxy_trade = proxy_trade.loc[proxy_trade.sec1 == sector]
        proxy_trade = proxy_trade.loc[proxy_trade.sec2.isin(['L','M','N','O','P'])]
        proxy_trade['sec1'] = ['sec'+x if x is not 'other' else 'other' for x in proxy_trade.sec1 ]
        proxy_trade['sec2'] = ['sec'+x if x is not 'other' else 'other' for x in proxy_trade.sec2 ]
        
        proxy_trade = proxy_trade.query("reg1 == reg2")    

        
        proxy_trade = proxy_trade[['year','sec1','reg1','sec2','reg2','gdp']]
        proxy_trade.columns = ['year','sector','region','sector','region','gdp']
        proxy_trade.to_csv(os.path.join(data_path,'mrio_analysis','proxy_trade_sec{}.csv'.format(sector)),index=False)
    
    else:
        proxy_trade = pd.DataFrame(columns=['year','gdp'],index= mi_index).reset_index()
        proxy_trade['year'] = 2016
        proxy_trade['gdp'] = 0
        proxy_trade = proxy_trade.query("reg1 != reg2")    
        proxy_trade = proxy_trade.loc[proxy_trade.sec1 == sector]
        proxy_trade = proxy_trade.loc[proxy_trade.sec2.isin(['L','M','N','O','P'])]
        proxy_trade['sec1'] = ['sec'+x if x is not 'other' else 'other' for x in proxy_trade.sec1 ]
        proxy_trade['sec2'] = ['sec'+x if x is not 'other' else 'other' for x in proxy_trade.sec2 ]
        
        proxy_trade = proxy_trade.query("reg1 == reg2")    

        proxy_trade = proxy_trade[['year','sec1','reg1','sec2','reg2','gdp']]
        proxy_trade.columns = ['year','sector','region','sector','region','gdp']

        proxy_trade.to_csv(os.path.join(data_path,'mrio_analysis','proxy_trade_{}.csv'.format(sector)),index=False)
        
# =============================================================================
# Create second version of MRIO for Argentina
# =============================================================================
        
p = subprocess.Popen(['mrio_disaggregate', 'settings_trade.yml'],
                     cwd=os.path.join(data_path, 'mrio_analysis'))
p.wait()

region_names_list = [item for sublist in [[x]*(len(sectors)+1) for x in region_names]
                     for item in sublist]

rows = ([x for x in sectors+['VA']])*len(region_names)
cols = ([x for x in sectors+['FD']])*len(region_names)

index_mi = pd.MultiIndex.from_arrays([region_names_list, rows], names=('region', 'row'))
column_mi = pd.MultiIndex.from_arrays([region_names_list, cols], names=('region', 'col'))

MRIO = pd.read_csv(os.path.join(data_path,'mrio_analysis','output2.csv'),header=None,index_col=None)
MRIO.index = index_mi
MRIO.columns = column_mi

# create predefined index and col, which is easier to read
sector_only = [x for x in sectors]*len(region_names)
col_only = ['FD']*len(region_names)

region_col = [item for sublist in [[x]*len(sectors) for x in region_names] for item in sublist] + \
    [item for sublist in [[x]*1 for x in region_names] for item in sublist]

column_mi_reorder = pd.MultiIndex.from_arrays(
    [region_col, sector_only+col_only], names=('region', 'col'))

# sum va and imports
valueA = pd.DataFrame(MRIO.loc[MRIO.index.get_level_values(1) == 'VA'].sum(axis='index'))
valueA.columns = pd.MultiIndex.from_product([['Total'],['ValueA']],names=['region','row'])

output = pd.concat([MRIO.loc[~MRIO.index.get_level_values(1).isin(['FD'])]])
output = output.drop('VA', level=1)
output = pd.concat([output,valueA.T])

output = output.reindex(column_mi_reorder, axis='columns')

''' Rebalance table'''
prov_ratios = pd.DataFrame((prov_data.iloc[:16,:24].stack().swaplevel(i=-2,
             j=-1)/sum(prov_data.iloc[:16,:24].stack().swaplevel(i=-2, 
             j=-1))),columns=['ratio']).reset_index().groupby(['level_0','level_1']).sum().reindex(output.index)[:384]

output_ratio = pd.DataFrame((output.sum(level=0,axis=1).sum(axis=1)[:-1]/sum(output.sum(level=0,axis=1).sum(axis=1)[:-1])),columns=['ratio'])

new_values = pd.DataFrame(output.sum(level=0,axis=1).sum(axis=1)[:-1],columns=['ratio']).multiply(prov_ratios).divide(output_ratio).fillna(0)

mrio_arg = ras_method(np.array(output).T,np.array(list(new_values.ratio)+list(output.sum(axis=0)[-24:])),
                      np.array(list(new_values.ratio)+[output.sum(axis=0)[384:].sum()]), eps=1e-5,print_out=False)

MRIO = pd.DataFrame(mrio_arg.T,columns=output.columns,index=output.index)

''' And save table '''
MRIO.to_csv(os.path.join(data_path,'economic_IO_tables','output','mrio_argentina.csv'))

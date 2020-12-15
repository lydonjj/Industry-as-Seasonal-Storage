import matplotlib
import matplotlib.pyplot as plt
from fredapi import Fred
import time
import pandas as pd
from eia import api
import re


class Fred_data(object):
    def __init__(self, naics):
        self.naics = naics

    #Gets FRED data and processes
    def findData(self):
        #Gets the series under Indusdrial Production & Capacity Utilization
        fred = Fred(api_key='e0a47670a791268b5b30cdf7cc217c4c')
        series = fred.search_by_category(3,order_by='title',filter=('frequency','Monthly')) #limit = 300

        #Keeps only the Manufacturing series. Removes unnecessary title info
        series = series[series['title'].str.startswith('Capacity Utilization: Manufacturing')]
        series['title'] = series['title'].str.replace('Capacity Utilization: Manufacturing: Durable Goods: ','')
        series['title'] = series['title'].str.replace('Capacity Utilization: Manufacturing: Non-Durable Goods: ','')

        #Gets the NAICS codes and series IDs for each series
        naics_code = series['title'].str.extract(r'\= (.{3})') #Some have pt. before ). Need to fix
        naics_code = naics_code.rename(columns = {0:'NAICS Code'})
        naics_code['NAICS Code'] = pd.to_numeric(naics_code['NAICS Code'], downcast = 'integer')
        series['title'] = series['title'].str.replace(r'\(([^)]+)\)','')
        series_id = series.index.tolist()

        #Makes a DataFrame with NAICS code, series ID, and title
        dataset = pd.DataFrame(series.iloc[:,3])
        dataset = naics_code.merge(dataset, left_index=True, right_index=True)

        #Gets data for each series from 1997 through 2018
        data = {}
        count = 0
        for id in series.index:
            data[id] = fred.get_series(id, observation_start='1997-01-01', observation_end='2019-12-01')
            count += 1
            if count == len(series)/2:
                time.sleep(10)

        data = pd.DataFrame(data)

        #Adds data to dataset and organizes by NAICS
        data_id = data.transpose()
        dataset['Series ID'] = series_id
        dataset = dataset.merge(data_id, left_index=True,right_index=True)
        dataset.index = naics_code['NAICS Code'].tolist()
        dataset = dataset.drop('NAICS Code',1)
        dataset = dataset.sort_index()
        dataset = dataset.rename(columns = {'title':'Industry'})

        return dataset

    #Retrieves data for specified NAICS code
    def getData(self):

        dataset = self.findData()
        data = dataset.loc[self.naics]

        return data, dataset

class EPA_data(object):
    def __init__(self, naics):
        self.naics = naics

    #Gets data from EPA summary spreadsheet and creates dataframe with NAICS code as index
    def findData(self):

        epa_data = pd.read_excel(r'/Users/John/Documents/Energy Research/2018_data_summary_spreadsheets/ghgp_data_by_year.xlsx',
        sheet_name='Direct Emitters', header=3, usecols='K,M:U', index_col=0)
        ids = epa_data.index.tolist()
        ids = [x // 1000 for x in ids] #Trims NAICS code to only include first 3 digits. Matches FRED data
        epa_data.index = ids
        epa_data = epa_data.rename(columns = {'Latest Reported Industry Type (sectors)':'Industry', '2018 Total reported direct emissions':'2018',
        '2017 Total reported direct emissions':'2017','2016 Total reported direct emissions':'2016','2015 Total reported direct emissions':'2015',
        '2014 Total reported direct emissions':'2014','2013 Total reported direct emissions':'2013','2012 Total reported direct emissions':'2012',
        '2011 Total reported direct emissions':'2011'}) #should update using .columns

        return epa_data

    #Retrieves data for specified NAICS code
    def getData(self):

        dataset = self.findData()
        data = dataset.loc[self.naics]

        return data, dataset

class EIA_data(object):
    def __init__(self, category):
         self.category = category

    #Gets data from EIA. Searches by category and gets series in each category
    def getData(self):

        myapikey = 'ba1be1ff6d258c3b793079d6fbc47131'

        cat = api.Category(category_id=self.category,apikey=myapikey)
        series = cat.to_dict()
        series = series['childseries']
        series = pd.DataFrame(series)
        if self.category != 40211: #Keeps only monthly datasets for electricity sales and gas
            series = series[series['series_id'].str.endswith('M')]
        series_ids = series['series_id'].tolist()

        #Extracts the state abbreviation for each series
        if self.category == 40211:
            states = series['series_id'].str.extract(r'(?<=\.)(.{2})(?=\.)')
        elif self.category == 1004:
            states = series['series_id'].str.extract(r'(?<=\.)(.{2})(?=\-)')
        else:
            states = series['series_id'].str.extract(r'(\w{2})(?=2)')

        #Gets series data
        data = {}
        dataset = pd.DataFrame()
        count = 0
        for id in series_ids:
            data = api.Series(id,apikey=myapikey)
            data = data.to_dataframe(include_metadata=True)
            dataset[states.iloc[count,0]] = data['value']
            count += 1
            if count == len(series_ids)/2:
                time.sleep(10)

        #Formats dates and converts to Btu
        if self.category != 40211:
            dataset.index = pd.to_datetime(data['period'], format = '%Y%m')
        else:
            dataset.index = data['period']
            dataset = dataset.drop(dataset.index[18:])
        if self.category == 1004:
            dataset = dataset * 3.4121416 #Convert million kWh to billion Btu

        return dataset

    #Sums monthly data to convert to annual
    def sumData(self):

        dataset = self.getData()
        sum = pd.DataFrame()

        for dates in dataset.index:
            year = dates.year
            if year == 2019 or year == 2020:
                dataset = dataset.drop([dates])
                continue
            sum[year] = dataset.loc[str(year)].sum()
        sum = sum.transpose()

        return sum, dataset

#Gets GDP data from BEA spreadsheets and finds state contributions to national GDP by industry
def BEA_getData():
    #states = ['AK', 'AL', 'AR','AZ','CA','CO','CT','DC','DE','FL',
    #'GA','HI','IA','ID','IL','IN','KS','KY','LA','MA','MD','ME',
    #'MI','MN','MO','MS','MT','NC','ND','NE','NH','NJ','NM','NV',
    #'NY','OH','OK','OR','PA','RI','SC','SD','TN','TX','US','UT',
    #'VA','VT','WA','WI','WV','WY']
    gdp_data = pd.read_excel(r'/Users/John/Documents/Energy Research/SAGDP2N.xls',
    header = 5, usecols = 'A,B,D:AA', keep_default_na = False)

    gdp_data = gdp_data.replace(to_replace = '(L)', value = 0)
    gdp_num = gdp_data.drop(columns = ['NAICS','GeoName','Description'])

    #Finds the percentage of National GDP contributed by each State for each industry
    count = 0
    tot = 0
    years = 0
    for ids in gdp_num.index:
        if ids > 1141:
            id = ids
        for col in gdp_num.columns:
            gdp_data.iloc[ids,years+3] = float(gdp_num.iloc[ids,years]) / float(gdp_num.iloc[tot,years]) #Divides each states gdp by national
            years += 1
        count += 1
        years = 0
        tot += 1
        if count == 22:
            tot = 0
            count = 0

    gdp_data.index = gdp_data['NAICS'].tolist()
    gdp_data = gdp_data.drop('NAICS',1)

    return gdp_data

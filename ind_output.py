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
        naics_code['NAICS Code'] = pd.to_numeric(naics_code['NAICS Code'])
        series['title'] = series['title'].str.replace(r'\(([^)]+)\)','')
        series_id = series.index.tolist()

        #Makes a DataFrame with NAICS code, series ID, and title
        dataset = pd.DataFrame(series.iloc[:,3])
        dataset = naics_code.merge(dataset, left_index=True, right_index=True)

        #Gets data for each series from Jan 2015 through 2018 (to match epa data)
        data = {}
        count = 0
        for id in series.index:
            data[id] = fred.get_series(id, observation_start='2011-01-01', observation_end='2018-12-01')
            count += 1
            if count == len(series)/2:
                time.sleep(10)

        data = pd.DataFrame(data)

        #Adds data to dataset and organizes by NAICS
        data_id = data.transpose()
        dataset['Series ID'] = series_id
        dataset = dataset.merge(data_id, left_index=True,right_index=True)
        naics_code = naics_code['NAICS Code'].tolist()
        dataset.index = naics_code
        dataset = dataset.drop('NAICS Code',1)
        dataset = dataset.sort_index()
        dataset = dataset.rename(columns = {'title':'Industry'})

        return dataset

    def getData(self):
        #Retrieves data for specified NAICS code
        dataset = self.findData()
        data = dataset.loc[self.naics]

        return data, dataset

class EPA_data(object):
    def __init__(self, naics):
        self.naics = naics

    def findData(self):
        #Gets data from EPA summary spreadsheet and creates dataframe with NAICS code as index
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

    def getData(self):
        #Retrieves data for specified NAICS code
        dataset = self.findData()
        data = dataset.loc[self.naics]

        return data, dataset

class EIA_data(object):
    def __init__(self, category):
         self.category = category

    def getData(self):
        #Gets data from EIA. Searches by category and gets series in each category
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

    def sumData(self):
        #Sums monthly data to convert to annual
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

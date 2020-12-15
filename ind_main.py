import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import ind_output as ind
from datetime import date
import matplotlib.ticker as ticker

#Gets FRED, EPA, and BEA data and organizes it. Takes average of capacity data and sum of emissions,
#and gets all NAICS codes from FRED and EPA. Also converts FRED data to annual and finds
#state level industrial capacity data using BEA GDP data.
def process(naics):

    cap = ind.Fred_data(naics)
    capacity, all_fred = cap.getData()
    capacity = capacity.mean(axis=0)

    emi = ind.EPA_data(naics)
    emissions, all_epa = emi.getData()
    emissions = emissions.sum(axis=0, numeric_only=True) / 1000
    emissions = emissions.sort_index()

    # dataset = capacity.append(emissions)
    # dataset = pd.DataFrame(dataset)
    # dataset = dataset.transpose()
    # dataset.index = naics

    #gdp = ind.BEA_data()
    gdp_percent = ind.BEA_getData()

    fred_num = all_fred.drop(columns = ['Industry', 'Series ID'])
    sum_fred = pd.DataFrame()
    annual_fred = pd.DataFrame()

    #Takes average of repeat NAICS codes in FRED data, then gets average of monthly data for each year.
    count = 0
    for id in fred_num.index:
        if id not in annual_fred.columns:
            sum_fred[id] = fred_num.iloc[fred_num.index.get_loc(id), :].mean()
        while count < len(fred_num.columns):
            annual_fred.loc[fred_num.columns[count].year, id] = sum_fred.iloc[count:count+12, sum_fred.columns.get_loc(id)].mean()
            count += 12
        count = 0

    annual_fred = annual_fred.transpose()
    annual_fred = annual_fred[annual_fred.index.notnull()] #Drops rows with unknown NAICS code
    state_cap = gdp_percent

    #Gets product of national capacity data and state gdp percentage to find state level capacity.
    for id in annual_fred.index:
        if int(id) in gdp_percent.index:
            for year in annual_fred.columns:
                state_cap.loc[int(id), str(year)] = annual_fred.loc[id, year] * gdp_percent.loc[int(id), str(year)]

    return capacity, emissions, all_fred, all_epa, state_cap

#Gets data for the three energy categories, finds percentage of total energy for sales and gas,
#and finds monthly average of total energy
def energy_process(category):

    e = ind.EIA_data(category[0])
    s = ind.EIA_data(category[1])
    g = ind.EIA_data(category[2])
    energy = e.getData()
    sales, monthly_sales = s.sumData()
    gas, monthly_gas = g.sumData()

    #Combines gas and sales data, uses only the states in common
    sum = sales.add(gas, fill_value = 0)
    states = set(energy.columns).intersection(set(sum.columns))
    percent = pd.DataFrame(columns = states, index = sum.index)
    percent = percent.sort_index(axis = 1)
    #Finds percentage of total energy not accounted for by sales and gas data
    for year in sum.index:
        for state in states:
            percent.loc[year, state] = sum.loc[year, state] / energy.loc[str(year), state]
    percent_energy = 1 - percent

    monthly_energy = energy.multiply(percent_energy) / 12 #Average total energy not in sales and gas per month
    monthly = monthly_sales.add(monthly_gas, fill_value = 0)
    #Gets total monthly energy
    for dates in monthly.index:
        year = dates.year
        monthly.loc[dates] = monthly.loc[dates].add(monthly_energy.loc[year], fill_value = 0)

    monthly = monthly.drop(monthly.columns[0], axis = 1)
    monthly = monthly.sum(axis = 1) #Combines all states to get national total

    return monthly, percent

#Makes plots for Capacity Utilization and Emissions of specified NAICS code, Capacity Utilization vs energy use,
#state energy use accounted by electricity and nat. gas, and state level capacity by NAICS code
def plotData(naics, category):

    #Gets FRED, EPA, and BEA data and organizes. Finds overall capacity data for 2018.
    capacity, emissions, all_fred, _, state_cap = process(naics)
    #all_fred.to_csv(r'/Users/John/Documents/Energy Research/all_capacity.csv')
    overall_cap = all_fred.iloc[36]
    overall_cap = overall_cap.drop(['Industry', 'Series ID'], axis = 0)
    overall_cap.index = pd.to_datetime(overall_cap.index, format = '%Y%m')
    overall_cap = overall_cap.iloc[84:96] #Data for 2018

    #Gets EIA data
    monthly_energy, percent = energy_process(category)
    monthly_energy = monthly_energy.iloc[0:12] #Data for 2018
    monthly_energy = monthly_energy.sort_index()
    percent = percent.iloc[0]
    percent = percent.transpose()

    #Selects BEA data for Alabama and given NAICS code
    state_cap = state_cap.loc[naics]
    state_cap = state_cap.loc[state_cap['GeoName'] == 'Alabama']
    state_cap = state_cap.drop(columns = ['GeoName', 'Description'])
    state_cap = state_cap.transpose()

    #Plots
    plt.figure(figsize=(5,3))
    fig1, ax1 = plt.subplots(2)
    fig1.autofmt_xdate()
    fig1.suptitle('Industrial Output 2011-2018 for NAICS Code %i' %int(naics[0]), y = .97)

    ax1[0].plot(capacity.index,capacity.values)
    ax1[0].set_title('Capacity Utilization')
    ax1[0].set_ylabel('Percent of Capacity')

    ax1[1].plot(emissions.index,emissions.values)
    ax1[1].set_title('Reported Emissions')
    ax1[1].set_xlabel('Date')
    ax1[1].set_ylabel('Emissions (kt CO2)')

    fig1.tight_layout()
    plt.savefig("Ind_production.png", dpi=300)

    plt.figure(figsize=(6,3))
    fig2, ax2 = plt.subplots()
    fig2.autofmt_xdate()
    fig2.suptitle('2018 National Industrial Capacity Utilization and Energy Use', y = .97)

    ax2.scatter(overall_cap.values, monthly_energy.values)
    ax2.set_xlabel('Percent of Capacity')
    ax2.set_ylabel('Energy Use (Billion Btu)')

    plt.savefig("Ind_cap_energy.png", dpi=300)

    plt.figure(figsize=(25,3))
    fig3, ax3 = plt.subplots()
    fig3.suptitle('2018 Percentage of Energy Use from Electricity and Natural Gas by State', y = .95)

    #ax3.xaxis.set_major_locator(ticker.MultipleLocator(1))
    ax3.bar(percent.index, percent.values)
    ax3.set_xlabel('State')
    ax3.set_ylabel('Percent of Total Energy')
    plt.xticks(rotation = 90, fontsize = 6)

    plt.savefig("State_sales_gas.png", dpi=300)

    plt.figure(figsize=(5,3))
    fig4, ax4 = plt.subplots()
    fig4.suptitle('Alabama Capacity Utilization for NAICS Code %i' %int(naics[0]), y =.95)

    ax4.plot(state_cap.index, state_cap.values)
    ax4.set_xlabel('Year')
    ax4.set_ylabel('Percent of National Capacity')
    plt.xticks(rotation = 90, fontsize = 10)

    plt.savefig("State_cap.png", dpi=300)

#Checks if NAICS codes match in FRED and EPA data
def codecheck(naics):

    _, _, _, all_fred, all_epa = process(naics)
    #print(all_fred)
    fr_code = all_fred.index.tolist()
    epa_code = all_epa.index.tolist()

    unmatched = []
    for id in epa_code:
         if id not in fr_code and id not in unmatched:
             unmatched.append(id)
    unmatched.sort()
    return unmatched


naics = [321] #Selects the Naics code to use. 321 is Naics code for wood product manufacturing
category = [40211,1004,480691] #EIA Category IDs for Total Industrial Energy, Industrial electricity sales,
#and Industrial natural gas consumption
plotData(naics, category)
#print(codecheck(naics))

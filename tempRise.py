
import sys
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt

class dataGroup():


    def __init__(self, input_df, prefix) -> None:
        
        self.start_index = 2  #!!! this must always be col 2 in the dataframe (the col which real data starts)
        self.input_df = input_df  #this is the filetracker.csv file
        self.prefix = prefix  #path to the actual data files 
        self.file_set = set(list(input_df.iloc[ :, 0]))
        self.dict_df, self.dict_samplerate = self.make_dict_df()  #!!! sample rate must be in same location
        self.derate_limit = 85
        self.hr_conversion = 1/3600
        self.min_conversion = 1/60
        self.temp_list = [20,30,40,50]  #temps to evaluate derate time
        self.at_time_temprise = 2 #time in hours at temprise reading
        pass

    def make_dict_df(self):
        dict_df = {}
        dict_samplerate = {}
        for i in range(len(self.input_df)): #read line by line of input_df
            filename = self.prefix + self.input_df['filename'][i]  #col 1 holds the names of the datafile .csv from the data logger
            temp_df = pd.read_csv(filename,low_memory = False) 
            filter = temp_df.iloc[ : , 0] == 'Scan Sweep Time (Sec)'
            index = list(filter).index(True) + 1
            filter2 = temp_df.iloc[ : , 0] == 'Scan Interval'
            index2 = list(filter2).index(True) 
            samplerate = temp_df.iloc[index2, 1]
            samplerate = int(float(samplerate[-6 : ]))
            temp_df = pd.read_csv(filename, skiprows = index)
            temp_df = temp_df.dropna(axis = 1, how = 'all')
            temp_df = temp_df.dropna(axis = 0)
            file = self.input_df['filename'][i]
            if file not in dict_df.keys():
                dict_df[file] = temp_df.iloc[ :, 0:2]
                dict_samplerate[file] = samplerate
            col_x = self.input_df['col_id'][i]  #col_id is column 4 in input_df
            dict_df[file] = dict_df[file].join(temp_df.iloc[ : , col_x])    
            
            cols = list(dict_df[file].columns)
            cols[-1] = '#' + str(self.input_df['cable_id'][i]) + ' ' + self.input_df['test_type'][i] + ' ' + self.input_df['label'][i]
            dict_df[file].columns = cols
 
            #print(dict_df[filename].columns) #[self.input_df[j,4]] = self.input_df[j, 5]  #label is column 5 in input_df
        return dict_df, dict_samplerate               

    def calculate_delta(self):
        delta = {}
        for i in self.dict_df.keys(): #i is a key corresponding to a filename)
            delta[i] = self.dict_df[i].iloc[ :, 0:2]   #create new data frame organized by a dictionary, include previous col 0 and col 1 of previous df 
            for j in range(len(self.dict_df[i].columns) - self.start_index):   #iterate thru columns    
                #print('i: ', i, 'j: ', j)
                temp = self.dict_df[i].iloc[ : , self.start_index + j] - self.dict_df[i].iloc[0, self.start_index + j]  #subtract from initial temp where time = 0
                delta[i] = delta[i].join(temp)

        return delta
    
    def calculate_derate_time(self):  
        derate_dct = {}
        for i in list(self.dict_df.keys()):
            derate_dct[i] = {}
            for j in self.temp_list:
                derate_dct[i][j] = {}
                #for k in range(self.stop_index[j] - self.start_index[j] + 2):

        delta_dct = self.calculate_delta()
        for i in list(self.dict_df.keys()): 
            for j in self.temp_list:
                col_num = len(self.dict_df[i].columns) - self.start_index
                for k in range(col_num):   #number of labels or headers to iterate
                    actual_index = k + self.start_index
                    #print('i: ', i, ' j: ', j, ' k: ', k, ' act_index: ', actual_index)
                    label = list(delta_dct[i].columns)[actual_index]
                    series_derate = delta_dct[i].iloc[ : , actual_index ] + j - self.derate_limit
                    bool_filter = series_derate > 0  #if result is pos then current temp is greater than derate temp
                    if bool_filter.iloc[-1] == False:
                        derate_dct[i][j][label] = ['no derating']
                    else:
                        samplerate = self.dict_samplerate[i]
                        time = series_derate[bool_filter].index[0] * samplerate * self.hr_conversion
                        derate_dct[i][j][label] = [time]
                               
        return derate_dct
            
            
    def make_temprise_table(self):
        #print('Temp rise deg C:\n')
        delta_dct = self.calculate_delta()
        for i in list(self.dict_df.keys()):
            hrs = delta_dct[i].iloc[ : , 1] * self.hr_conversion
            indx = len(list(hrs[hrs < self.at_time_temprise]))
            print('Temp rise deg C at ', indx * self.hr_conversion, ' hrs')
            print(delta_dct[i].iloc[indx-1, 2: ], '\n')
        return
    
    def make_derate_table(self):
        derate_dct = self.calculate_derate_time()
        dct_derate_tab = {}

        for i in self.dict_df.keys():  #iterates the number of files, i
            if i not in dct_derate_tab.keys():
                dct_derate_tab[i] = pd.DataFrame()
            for j in self.temp_list:  #iterates thru the temp derating constants i.e.[20,30,40,50]
                dct_derate_tab[i] = pd.concat([dct_derate_tab[i],pd.DataFrame(derate_dct[i][j])], axis = 0)
            dct_derate_tab[i].index = self.temp_list
            #print(type(dct_derate_tab[i]))
        return dct_derate_tab
            
    def plotchart2(self, plot_title, dict_df, dict_keylist = [], index_ylist = [], index_x = 1):
        '''
        parameters:
            plot_title: your chosen title for plot
            dict_df: a dictionary of data frames
            dict_keylist: do not use unless you want a subset of dict_df (code not completed)
            index_ylist:  do not use unless you want a subset of dict_df (code not completed)
            index_x: x data must start at column 1 !!!
            
        
        overview: plot dataframe by supplying a dictionary of dataframes, select single xdata index for horizontal axis and plot multiple y data (vertical axis)
        output: fig, ax 

        '''
        if dict_keylist == []: #if none specified plot data from all files
            dict_keylist = list(dict_df.keys())
        #if index_ylist = []:  save for another feature ...
           
        fig, ax = plt.subplots(figsize = (8, 6),layout = 'constrained')
        for i in dict_keylist:  #iterate thru dataframes via dictionary keys which in case are file names
            for j in range(len(dict_df[i].columns) - self.start_index):   #iterate thru columns to plot
                xdata = dict_df[i].iloc[ : , index_x] * self.dict_samplerate[i] / 3600    #time in hours important!!! make sure you are using the right sampling rate conversion, depends on logger setting
                ydata = dict_df[i].iloc[ : , self.start_index + j]
                ax.plot(xdata, ydata, label = list(dict_df[i].columns)[self.start_index + j])
                
        ax.legend()    
        ax.set_xlabel('Hours')  # Add an x-label to the axes.
        ax.set_ylabel('Temp deg C')  # Add a y-label to the axes.
        ax.set_title(plot_title)  # Add a title to the axes.
        return fig, ax

    def resize(self, fig, ax, xlim, ylim):
        ax.set_ylim(ylim[0], ylim[1])
        ax.set_xlim(xlim[0], xlim[1])
        return fig, ax

    def saveplot(self, fig, ax, filename=0):
            if filename == 0:
                fig.savefig('./figs/' + 'plot00' + '.png', dpi = 200) 
            else:
                fig.savefig(filename + '.png', dpi = 200)
            return      
    
    def deconstructor():  #need to add
        return
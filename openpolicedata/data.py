import os.path as path
import pandas as pd
from datetime import datetime

if __name__ == '__main__':
    import data_loaders
    import _datasets
    # import preproc
    from defs import TableType, DataType, MULTI
else:
    from . import data_loaders
    from . import _datasets
    # from . import preproc
    from .defs import TableType, DataType, MULTI

class Table:
    """
    A class that contains a DataFrame for a dataset along with meta information

    Attributes
    ----------
    details : pandas Series
        Series containing information about the dataset
    state : str
        Name of state where agencies in table are
    source_name : str
        Name of source
    agency : str
        Name of agency
    table_type : TableType enum
        Type of data contained in table
    year : int, list, MULTI
        Indicates years contained in table
    description : str
        Description of data source
    url : str
        URL where table was accessed from
    table : pandas of geopandasDataFrame
        Data accessed from source

    Methods
    -------
    to_csv(output_dir=None, filename=None)
        Convert table to CSV file
    get_csv_filename()
        Get default name of CSV file
    """

    details = None
    state = None
    source_name = None
    agency = None
    table_type = None
    year = None
    description = None
    url = None

    # Data
    table = None

    # From source
    _data_type = None
    _dataset_id = None
    _date_field = None
    _agency_field = None

    def __init__(self, source, table=None, year_filter=None, agency_filter=None):
        '''Construct Table object
        This is intended to be generated by the Source.load_from_url and Source.load_from_csv classes

        Parameters
        ----------
        source : pandas or geopandas Series
            Series containing information on the source
        table : pandas or geopandas 
            Name of state where agencies in table are
        '''
        if not isinstance(source, pd.core.frame.DataFrame) and \
            not isinstance(source, pd.core.series.Series):
            raise TypeError("data must be an ID, DataFrame or Series")
        elif isinstance(source, pd.core.frame.DataFrame):
            if len(source) == 0:
                raise LookupError("DataFrame is empty")
            elif len(source) > 1:
                raise LookupError("DataFrame has more than 1 row")

            source = source.iloc[0]

        self.details = source
        self.table = table

        self.state = source["State"]
        self.source_name = source["SourceName"]

        if agency_filter != None:
            self.agency = agency_filter
        else:
            self.agency = source["Agency"]

        self.table_type = TableType(source["TableType"])  # Convert to Enum

        if year_filter != None:
            self.year = year_filter
        else:
            self.year = source["Year"]

        self.description = source["Description"]
        self.url = source["URL"]
        self._data_type = DataType(source["DataType"])  # Convert to Enum

        if not pd.isnull(source["dataset_id"]):
            self._dataset_id = source["dataset_id"]

        if not pd.isnull(source["date_field"]):
            self._date_field = source["date_field"]
        
        if not pd.isnull(source["agency_field"]):
            self._agency_field = source["agency_field"]


    def to_csv(self, output_dir=None, filename=None):
        '''Export table to CSV file. Use default filename for data that will
        be reloaded as an openpolicedata Table object

        Parameters
        ----------
        output_dir - str
            (Optional) Output directory. Default: current directory
        filename - str
            (Optional) Filename. Default: Result of get_csv_filename()
        '''
        if filename == None:
            filename = self.get_csv_filename()
        if output_dir != None:
            filename = path.join(output_dir, filename)
        if not isinstance(self.table, pd.core.frame.DataFrame):
            raise ValueError("There is no table to save to CSV")

        self.table.to_csv(filename, index=False)


    def get_csv_filename(self):
        '''Generate default filename based on table parameters

        Returns
        -------
        str
            Filename
        '''
        return get_csv_filename(self.state, self.source_name, self.agency, self.table_type, self.year)


class Source:
    """
    Class for exploring a data source and loading its data

    ...

    Attributes
    ----------
    datasets : pandas or geopandas DataFrame
        Contains information on datasets available from the source

    Methods
    -------
    get_tables_types()
        Get types of data availble from the source
    get_years()
        Get years available for 1 or more datasets
    get_agencies()
        Get agencies available for 1 or more datasets
    load_from_url()
        Load data from URL
    load_from_csv()
        Load data from a previously saved CSV file
    """

    datasets = None
    __limit = None

    def __init__(self, source_name, state=None):
        '''Constructor for Source class

        Parameters
        ----------
        source_name - str
            Source name from datasets table
        state - str
            (Optional) Name of state. Only necessary if source_name is not unique.

        Returns
        -------
        Source object
        '''
        self.datasets = _datasets.datasets_query(source_name=source_name, state=state)

        # Ensure that all sources are from the same state
        if len(self.datasets) == 0:
            raise ValueError("No Sources Found")
        elif self.datasets["State"].nunique() > 1:
            raise ValueError("Not all sources are from the same state")


    def get_tables_types(self):
        '''Get types of data availble from the source

        Returns
        -------
        list
            List containing types of data available from source
        '''
        return list(self.datasets["TableType"].unique())


    def get_years(self, table_type):
        '''Get years available for 1 or more datasets

        Parameters
        ----------
        table_type - str or TableType enum
            (Optional) If set, only returns years for requested table type

        Returns
        -------
        list
            List of years available for 1 or more datasets
        '''
        if isinstance(table_type, TableType):
            table_type = table_type.value

        dfs = self.datasets
        if table_type != None:
            dfs = self.datasets[self.datasets["TableType"]==table_type]

        all_years = list(dfs["Year"])
        years = set()
        for k in range(len(all_years)):
            if all_years[k] != MULTI:
                years.add(all_years[k])
            else:
                df = dfs.iloc[k]

                data_type =DataType(df["DataType"])
                url = df["URL"]
                if not pd.isnull(df["date_field"]):
                    date_field = df["date_field"]
                else:
                    raise ValueError("No date_field is provided to identify the years")
                
                if data_type ==DataType.CSV:
                    raise NotImplementedError("This needs to be tested before use")
                    if force_read:                    
                        table = pd.read_csv(url, parse_dates=True)
                        new_years = table[date_field].dt.year
                        new_years = new_years.unique()
                    else:
                        raise ValueError("Getting the year of a CSV files requires reading in the whole file. " +
                                        "Loading in the table may be a better option. If getYears is still desired " +
                                        " for this case, use forceRead=True")    
                elif data_type ==DataType.ArcGIS:
                        new_years = data_loaders.get_years_argis(url, date_field)
                elif data_type ==DataType.SOCRATA:
                        new_years = data_loaders.get_years_socrata(url, df["dataset_id"], date_field)
                else:
                    raise ValueError(f"Unknown data type: {data_type}")

                years.update(new_years)
            
        years = list(years)
        years.sort()

        return years


    def get_agencies(self, table_type=None, year=None, partial_name=None):
        '''Get agencies available for 1 or more datasets

        Parameters
        ----------
        table_type - str or TableType enum
            (Optional) If set, only returns agencies for requested table type
        year - int or the string "MULTI" or "N/A"
            (Optional)  If set, only returns agencies for requested year
        table_type - str or TableType enum
            (Optional) If set, only returns agencies for requested table type
        partial_name - str
            (Optional)  If set, only returns agencies containing the substring
            partial_name for datasets that contain multiple agencies

        Returns
        -------
        list
            List of agencies available for 1 or more datasets
        '''

        if isinstance(table_type, TableType):
            table_type = table_type.value

        src = self.datasets
        if table_type != None:
            src = self.datasets[self.datasets["TableType"]==table_type]

        if year != None:
            src = src[src["Year"] == year]

        if len(src) == 1:
            src = src.iloc[0]
        else:
            raise ValueError("table_type and year inputs must filter for a single source")            

        # If year is multi, need to use self._agencyField to query URL
        # Otherwise return self.agency
        if src["Agency"] == MULTI:
            data_type =DataType(src["DataType"])
            if data_type ==DataType.CSV:
                raise NotImplementedError(f"Unable to get agencies for {data_type}")
            elif data_type ==DataType.ArcGIS:
                raise NotImplementedError(f"Unable to get agencies for {data_type}")
            elif data_type ==DataType.SOCRATA:
                if partial_name is not None:
                    opt_filter = "agency_name LIKE '%" + partial_name + "%'"
                else:
                    opt_filter = None

                select = "DISTINCT " + src["agency_field"]
                if year == MULTI:
                    year = None
                agencySet = data_loaders.load_socrata(src["URL"], src["dataset_id"], 
                    date_field=src["date_field"], year=year, opt_filter=opt_filter, select=select, output_type="set")
                return list(agencySet)
            else:
                raise ValueError(f"Unknown data type: {data_type}")
        else:
            return [src["Agency"]]
        

    def load_from_url(self, year, table_type=None, agency_filter=None):
        '''Load data from URL

        Parameters
        ----------
        year - int or length 2 list or the string "MULTI" or "N/A"
            Used to identify the requested dataset if equal to its year value
            Otherwise, for datasets containing multiple years, this filters 
            the return data for a specific year (int input) or a range of years
            [X,Y] to return data for years X to Y
        table_type - str or TableType enum
            (Optional) If set, requested dataset will be of this type
        agency_filter - str
            (Optional) If set, for datasets containing multiple agencies, data will
            only be returned for this agency

        Returns
        -------
        Table
            Table object containing the requested data
        '''

        return self.__load(year, table_type, agency_filter, True)

    def __load(self, year, table_type, agency_filter, load_table):
        if isinstance(table_type, TableType):
            table_type = table_type.value

        src = self.datasets
        if table_type != None:
            src = src[self.datasets["TableType"] == table_type]

        if isinstance(year, list):
            matchingYears = src["Year"] == year[0]
            for y in year[1:]:
                matchingYears = matchingYears | (src["Year"] == y)
        else:
            matchingYears = src["Year"] == year

        filter_by_year = not matchingYears.any()
        if not filter_by_year:
            # Use source for this specific year if available
            src = src[matchingYears]
        else:
            # If there are not any years corresponding to this year, check for a table
            # containing multiple years
            src = src.query("Year == '" + MULTI + "'")

        if isinstance(src, pd.core.frame.DataFrame):
            if len(src) == 0:
                raise ValueError(f"There are no sources matching tableType {table_type} and year {year}")
            elif len(src) > 1:
                raise ValueError(f"There is more than one source matching tableType {table_type} and year {year}")
            else:
                src = src.iloc[0]

        # Load data from URL. For year or agency equal to multi, filtering can be done
        data_type =DataType(src["DataType"])
        url = src["URL"]

        if filter_by_year:
            year_filter = year
        else:
            year_filter = None

        if not pd.isnull(src["dataset_id"]):
            dataset_id = src["dataset_id"]

        table_year = None
        if not pd.isnull(src["date_field"]):
            date_field = src["date_field"]
            if year_filter != None:
                table_year = year_filter
        else:
            date_field = None
        
        table_agency = None
        if not pd.isnull(src["agency_field"]):
            agency_field = src["agency_field"]
            if agency_filter != None and data_type !=DataType.ArcGIS:
                table_agency = agency_filter
        else:
            agency_field = None
        
        #It is assumed that each data loader method will return data with the proper data type so date type etc...
        if load_table:
            if data_type ==DataType.CSV:
                table = data_loaders.load_csv(url, date_field=date_field, year_filter=year_filter, 
                    agency_field=agency_field, agency_filter=agency_filter, limit=self.__limit)
            elif data_type ==DataType.ArcGIS:
                table = data_loaders.load_arcgis(url, date_field, year_filter, limit=self.__limit)
            elif data_type ==DataType.SOCRATA:
                opt_filter = None
                if agency_filter != None and agency_field != None:
                    opt_filter = agency_field + " = '" + agency_filter + "'"

                table = data_loaders.load_socrata(url, dataset_id, date_field=date_field, year=year_filter, opt_filter=opt_filter, 
                    limit=self.__limit)
            else:
                raise ValueError(f"Unknown data type: {data_type}")

            table = _check_date(table, date_field)                        
        else:
            table = None

        return Table(src, table, year_filter=table_year, agency_filter=table_agency)


    def load_from_csv(self, year, output_dir=None, table_type=None, agency_filter=None):
        '''Load data from previously saved CSV file
        
        Parameters
        ----------
        year - int or length 2 list or the string "MULTI" or "N/A"
            Used to identify the requested dataset if equal to its year value
            Otherwise, for datasets containing multiple years, this filters 
            the return data for a specific year (int input) or a range of years
            [X,Y] to return data for years X to Y
        output_dir - str
            (output_dirOptional) Directory where CSV file is stored
        table_type - str or TableType enum
            (Optional) If set, requested dataset will be of this type
        agency_filter - str
            (Optional) If set, for datasets containing multiple agencies, data will
            only be returned for this agency

        Returns
        -------
        Table
            Table object containing the requested data
        '''

        table = self.__load(year, table_type, agency_filter, False)

        filename = table.get_csv_filename()
        if output_dir != None:
            filename = path.join(output_dir, filename)            

        table.table = pd.read_csv(filename, parse_dates=True)
        table.table = _check_date(table.table, table._date_field)  

        return table

    def get_csv_filename(self, year, output_dir=None, table_type=None, agency_filter=None):
        '''Get auto-generated CSV filename
        
        Parameters
        ----------
        year - int or length 2 list or the string "MULTI" or "N/A"
            Used to identify the requested dataset if equal to its year value
            Otherwise, for datasets containing multiple years, this filters 
            the return data for a specific year (int input) or a range of years
            [X,Y] to return data for years X to Y
        output_dir - str
            (Optional) Directory where CSV file is stored
        table_type - str or TableType enum
            (Optional) If set, requested dataset will be of this type
        agency_filter - str
            (Optional) If set, for datasets containing multiple agencies, data will
            only be returned for this agency

        Returns
        -------
        str
            Auto-generated CSV filename
        '''

        table = self.__load(year, table_type, agency_filter, False)

        filename = table.get_csv_filename()
        if output_dir != None:
            filename = path.join(output_dir, filename)             

        return filename

def _check_date(table, date_field):
    if date_field != None and len(table)>0:
        dts = table[date_field]
        dts = dts[dts.notnull()]
        if len(dts) > 0:
            one_date = dts.iloc[0]            
            if type(one_date) == str:
                table = table.astype({date_field: 'datetime64[ns]'})
                dts = table[date_field]
                dts = dts[dts.notnull()]
                one_date = dts.iloc[0]
            elif date_field.lower() == "year":
                try:
                    float(one_date)
                except:
                    raise
                
                table[date_field] = table[date_field].apply(lambda x: datetime(x,1,1))
                dts = table[date_field]
                dts = dts[dts.notnull()]
                one_date = dts.iloc[0]
                
            # Replace bad dates with NaT
            table[date_field].replace(datetime.strptime('1900-01-01 00:00:00', '%Y-%m-%d %H:%M:%S'), pd.NaT, inplace=True)
            dts = table[date_field]
            dts = dts[dts.notnull()]

            if len(dts) > 0:
                one_date = dts.iloc[0] 
                if hasattr(one_date, "year"):
                    if one_date.year < 1995:
                        raise ValueError("Date is before 1995. There was likely an issue in the date conversion")
                    elif one_date.year > datetime.now().year:
                        raise ValueError("Date is after the current year. There was likely an issue in the date conversion")
                else:
                    raise TypeError("Unknown data type for date")

    return table


def get_csv_filename(state, source_name, agency, table_type, year):
    '''Get default CSV filename for the given parameters. Enables reloading of data from CSV.
    
    Parameters
    ----------
    state - str
        Name of state
    source_name - str
        Name of source
    agency - str
        Name of agency
    table_type - str or TableType enum
        Type of data
    year = int or length 2 list or the string "MULTI" or "N/A"
        Year of data to load, range of years of data to load as a list [X,Y]
        to load years X to Y, or a string to indicate all of multiple year data
        ("MULTI") or a dataset that has no year filtering ("N/A")

    Returns
    -------
    str
        Default CSV filename
    '''
    if isinstance(table_type, TableType):
        table_type = table_type.value
        
    filename = f"{state}_{source_name}"
    if source_name != agency:
        filename += f"_{agency}"
    filename += f"_{table_type}"
    if isinstance(year, list):
        filename += f"_{year[0]}_{year[-1]}"
    else:
        filename += f"_{year}"

    # Clean up filename
    filename = filename.replace(",", "_").replace(" ", "_").replace("__", "_").replace("/", "_")

    filename += ".csv"

    return filename

if __name__ == '__main__':
    from datetime import date
    datasets = _datasets.datasets_query()
    max_num_stanford = 1
    num_stanford = 0
    prev_sources = []
    prev_tables = []
    output_dir = ".\\data"
    action = "standardize"
    for i in range(len(datasets)):
        if "stanford.edu" in datasets.iloc[i]["URL"]:
            num_stanford += 1
            if num_stanford > max_num_stanford:
                continue

        srcName = datasets.iloc[i]["SourceName"]
        state = datasets.iloc[i]["State"]

        if datasets.iloc[i]["Agency"] == MULTI and srcName == "Virginia":
            # Reduce size of data load by filtering by agency
            agency_filter = "Fairfax County Police Department"
        else:
            agency_filter = None

        skip = False
        for k in range(len(prev_sources)):
            if srcName == prev_sources[k] and datasets.iloc[i]["TableType"] ==prev_tables[k]:
                skip = True

        if skip:
            continue

        prev_sources.append(srcName)
        prev_tables.append(datasets.iloc[i]["TableType"])

        table_print = datasets.iloc[i]["TableType"]
        now = datetime.now().strftime("%d.%b %Y %H:%M:%S")
        print(f"{now }Saving CSV for dataset {i} of {len(datasets)}: {srcName} {table_print} table")

        src = Source(srcName, state=state)

        if action == "standardize":
            if datasets.iloc[i]["DataType"] ==DataType.CSV.value:
                table = src.load_from_csv(datasets.iloc[i]["Year"], datasets.iloc[i]["TableType"])
            else:
                year = date.today().year
                for y in range(year, year-20, -1):
                    csv_filename = src.get_csv_filename(y, output_dir, datasets.iloc[i]["TableType"], 
                        agency_filter=agency_filter)
                    if path.exists(csv_filename):
                        table = src.load_from_csv(y, table_type=datasets.iloc[i]["TableType"], 
                            agency_filter=agency_filter,output_dir=output_dir)
                        break

            table.standardize()
        else:
            if datasets.iloc[i]["DataType"] ==DataType.CSV.value:
                csv_filename = src.get_csv_filename(datasets.iloc[i]["Year"], output_dir, datasets.iloc[i]["TableType"])
                if path.exists(csv_filename):
                    continue
                table = src.load_from_url(datasets.iloc[i]["Year"], datasets.iloc[i]["TableType"])
            else:
                years = src.get_years(datasets.iloc[i]["TableType"])
                
                if len(years)>1:
                    # It is preferred to to not use first or last year that start and stop of year are correct
                    year = years[-2]
                else:
                    year = years[0]

                csv_filename = src.get_csv_filename(year, output_dir, datasets.iloc[i]["TableType"], 
                                        agency_filter=agency_filter)

                if path.exists(csv_filename):
                    continue

                table = src.load_from_url(year, datasets.iloc[i]["TableType"], 
                                        agency_filter=agency_filter)

            table.to_csv(".\\data")

    print("data main function complete")

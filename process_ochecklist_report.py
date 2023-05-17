import sys
import ftplib
import yaml
from typing import Tuple
from io import StringIO
import psycopg2
import logging
from config import ftp_server_credentials, quickevent_db_config
import datetime

"""
Process report from the mobile app O-checklist and update data in quickevent database
Usage: 
"""

def main() -> None:
    downloaded_file = download_file_from_ftp(**ftp_server_credentials)
    changes = process_downloaded_yaml(downloaded_file)
    generateHtmlReport(changes)

def download_file_from_ftp(server, login, password, subfolder='/'):
    """
    Get file from ftp server
    :param server: ftp server
    :param login: Username
    :param password: password
    :param subfolder: downloaded file location
    :return: list of downloaded file content
    """

    downloaded_files = []
    # Connect to the FTP server
    ftp = ftplib.FTP(server, login, password)

    # Change to the directory where the file is located (if necessary)
    ftp.cwd(subfolder)

    # Download the file from the FTP server and write it to the StringIO object
    def write_file_data(data):
        downloaded_file.write(data.decode('utf-8'))

    # Get a list of all YAML files in the directory
    filenames = ftp.nlst('*.yaml')
    for filename in filenames:
        # Create a StringIO object to hold the contents of the downloaded file
        downloaded_file = StringIO()

        # Download the file
        ftp.retrbinary('RETR ' + filename, write_file_data)

        # Retrieve the contents of the StringIO object as a string
        downloaded_files.append(downloaded_file.getvalue())

    # Close the FTP connection
    ftp.quit()

    return downloaded_files

def process_downloaded_yaml(downloaded_files):
    """
    Iterates over all downloaded file and separates changes - dns, late starts, changes cards and new comments
    :param downloaded_files: list of contents of downloaded yaml files
    :return: dictionary of lists with changes by type
    """

    # Results storage
    started_ok = []
    changes_cards = []
    changes_dns = []
    changes_late_start = []
    changes_comments = []

    changes_timestamps = []
    changes_creators = []

    changes = {}

    for file in downloaded_files:
        # Load the contents of the downloaded YAML file
        downloaded_data = yaml.safe_load(file)

        # Access report data
        report_data = downloaded_data['Data']
        for runner in report_data:
            if runner['ChangeLog'] is not None:
                # New card
                if 'NewCard' in runner['Runner']:
                    changes_cards.append([runner['Runner']['Id'], runner['ChangeLog']['NewCard'], runner['Runner']['Name'], runner['Runner']['Org'],runner['Runner']['Card'], runner['Runner']['NewCard']])
                # # DNS
                if 'DNS' in runner['Runner']['StartStatus']:
                    changes_dns.append([runner['Runner']['Id'], runner['ChangeLog']['DNS'], runner['Runner']['Name'], runner['Runner']['Org'],runner['Runner']['Card']])
                # # Late start
                if 'Late start' in runner['Runner']['StartStatus']:
                    changes_late_start.append([runner['Runner']['Id'], runner['ChangeLog']['LateStart'], runner['Runner']['Name'], runner['Runner']['Org'],runner['Runner']['Card']])
                # # Comment
                if 'Comment' in runner['Runner']:
                    changes_comments.append([runner['Runner']['Id'], runner['ChangeLog']['Comment'], runner['Runner']['Name'], runner['Runner']['Org'], runner['Runner']['Card'], runner['Runner']['Comment']])

            # Store started runners
            else:
                started_ok.append(runner['Runner']['Name'] + ', ' + runner['Runner']['Org'])

        changes['changed_cards'] = changes_cards
        changes['dns'] = changes_dns
        changes['late_starts'] = changes_late_start
        changes['comments'] = changes_comments

        changes_timestamps.append(downloaded_data['Created'])
        changes_creators.append(downloaded_data['Creator'])

    def get_report_timestamp(timestamps):
        joined_timestamps = []
        for timestamp in timestamps:
            joined_timestamps.append(timestamp.strftime('%d.%m.%Y %H:%M:%S'))
        return ', '.join(joined_timestamps)

    def get_used_app_versions(changes_creators):
        app_name = ''
        versions = []
        for creator in changes_creators:
            if " ".join(creator.split()[:-1]) != app_name:
                app_name = " ".join(creator.split()[:-1])
            if creator.split()[-1] not in versions:
                versions.append(creator.split()[-1])

        return app_name + ' ' + ', '.join(versions)

    changes['timestamp'] = get_report_timestamp(changes_timestamps)
    changes['creator'] = get_used_app_versions(changes_creators)

    # Get statistics
    print(f"Event statistics:\n"
          f"- started runners: {len(started_ok)}\n"
          f"- dns: {len(changes_dns)}\n"
          f"- cards changes: {len(changes_cards)}\n"
          f"- late starts: {len(changes_late_start)}\n"
          f"- new comments: {len(changes_comments)}")

    return changes

def format_timestamp(dt):
    """
    Handle
    :param dt: datetime from report, can be both datetime.datetime and string (if missing seconds)
    :return: Formated timestamp
    """
    # Handle if string
    if isinstance(dt, str):
        # Handle case without seconds
        if len(dt.split(':')) > 3:
            timestamp = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M%z")
        # Handle case with seconds
        else:
            timestamp = datetime.datetime.strptime(dt, "%Y-%m-%dT%H:%M%S%z")
        # Handle case without seconds
        if timestamp.second == 0:
            formatted_time = timestamp.strftime("%d.%m.%d %H:%M")
        # Handle case with seconds
        else:
            formatted_time = timestamp.strftime("%d.%m.%d %H:%M:%S")
    # Handle case without seconds
    elif dt.second == 0:
        formatted_time = dt.strftime("%d.%m.%d %H:%M")

    # Handle case with seconds
    else:
        formatted_time = dt.strftime("%d.%m.%d %H:%M:%S")
    return formatted_time

def generateHtmlReport(changes):
    """
    Create html report with changes from the start in hrml format which is more readable.
    :param changes:
    :return: html_file
    """

    html_file_template = '''
        <!DOCTYPE html>
        <html>
            <head>
                <meta http-equiv='Content-Type' content='text/html; charset=utf-8' />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" />                
                {style}                
                <title>{heading}</title>
            </head>
            <body onload="sortTable(0, 'dataDNS'),sortTable(0, 'dataCards'),sortTable(0, 'dataLateStart'),sortTable(0, 'dataComments')">
                <header>
                    <h1>{heading}</h1>
                    <h2>{time_stamp}</h2>
                </header>                
                <!-- Nestartující -->
                <section>{content_dns}</section>                

                <!-- Změny čipů -->
                <section>{content_cards}</section>                

                <!-- Pozdní starty -->
                <section>{content_late_start}</section>                

                <!-- Komentáře -->
                <section>{content_comments}</section>

                <footer>
                    <p>Created with script by Cáš based on report from app {creator}</p>
                </footer>
                {javascript}
            </body>
        </html>
    '''

    html_style = '''
    <style type='text/css'>
    * {
                        box-sizing: border-box;
                    }
            
                    html {
                        font-family: "Roboto", sans-serif;
                    }
            
                    body {
                        margin: 0px;
                        max-width: 1000px;
                    }
            
                    @media screen and (min-width: 801px) {
                        h1 {
                            font-size: 30px;
                        }
            
                        h2 {
                            font-size: 20px;
                        }
                    }
            
                    @media screen and (max-width: 800px) {
                        h1 {
                            font-size: 4vw;
                        }
            
                        h2 {
                            font-size: 3vw;
                        }
                    }
            
                    @media only screen and (max-width: 600px) {
                        th.card,
                        th.club,            
                        td.card,
                        td.club {
                            display: none;
                        }
                    }
            
                    h1 {
                        margin: 5px 0px;
                    }
            
                    h2 {
                        margin: 5px 0px;
                    }
            
                    header {
                        padding: 1px 15px;
                        margin-top: 5px;
                    }
        
                    footer {
                        padding: 1px 15px;
                        margin: 5px 15px;
                        border-radius: 5px;
                        background-color: #d3d3d3;
                        font-size: 12px;
                    }
            
                    section {
                        padding: 10px 15px;
                        margin: 0px 0px;
                        page-break-inside: avoid;
                    }
            
                    table,
                    tr,
                    td {
                        border-collapse: collapse;
                        padding: 2px;
                    }
            
                    table {
                        width: 100%;
                    }
            
                    td.name,
                    td.club {
                        width: 30%;
                    }
            
                    td.card {
                        width: 15%;
                    }
                    
                    th,
                    td {
                        text-align: left;
                    }
                    
                    td.nodata {
                        background-color: #d3d3d3;
                        border-radius: 5px;
                    }
                    
                    td.oldcard {
                        text-decoration: line-through;
                    }
            
                    tr:nth-child(even) {
                        background-color: #f2f2f2;
                    }
            
                    p.cat-title {
                        background-color: #139c17;
                        ;
                        margin: 10px 0px 5px 0px;
                        padding: 5px;
                        border-radius: 5px;
                        position: relative;
                    }
            
                    p.cat-title span.category {
                        font-weight: bold;
                        font-size: 1.5em;
                    }
            
                    p.cat-title span.controls {
                        font-size: 1.0em;
                        position: absolute;
                        right: 5px;
                        bottom: 5px;
                    }
            </style>
    '''

    html_javascript = '''
    <script>
        function sortTable(columnIndex, tableId) {
            var table, rows, switching, i, x, y, shouldSwitch;
            table = document.getElementById(tableId);
            switching = true;
            while (switching) {
              switching = false;
              rows = table.rows;
              for (i = 1; i < rows.length - 1; i++) {
                shouldSwitch = false;
                x = rows[i].getElementsByTagName("TD")[columnIndex];
                y = rows[i + 1].getElementsByTagName("TD")[columnIndex];
                if (x.innerHTML.toLowerCase() > y.innerHTML.toLowerCase()) {
                  shouldSwitch = true;
                  break;
                }
              }
              if (shouldSwitch) {
                rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                switching = true;
              }
            }
        }
        
        // Function to store table row status in local storage
        function saveTableRowStatus(tableId, rowId, checked) {
            const key = `${tableId}-${rowId}`; // Create a unique key using tableId and rowId
            if (checked) {
              localStorage.setItem(key, true); // Store the status in local storage
            } else {
              localStorage.removeItem(key); // Remove the status from local storage
            }
        }
          
        // Function to load table row status from local storage
        function loadTableRowStatus(tableId, rowId) {
          const key = `${tableId}-${rowId}`; // Create the unique key
          return localStorage.getItem(key) === 'true'; // Return the stored status as boolean
        }
        
        // Get all the checkboxes
        const checkboxes = document.querySelectorAll('.solved');
        
        // Add event listener to each checkbox
        checkboxes.forEach((checkbox) => {
          checkbox.addEventListener('change', (event) => {
            const row = event.target.parentElement.parentElement; // Get the row element
            const rowId = row.id; // Get the id of the row
            const tableId = row.closest('table').id; // Get the id of the parent table
            const checked = event.target.checked; // Get the checkbox checked status
            saveTableRowStatus(tableId, rowId, checked); // Save the table row status to local storage
          });
        });
        
        // Load the table row status from local storage and tick the checkboxes
        checkboxes.forEach((checkbox) => {
          const row = checkbox.parentElement.parentElement; // Get the row element
          const rowId = row.id; // Get the id of the row
          const tableId = row.closest('table').id; // Get the id of the parent table
          const storedStatus = loadTableRowStatus(tableId, rowId); // Load the stored status from local storage
          checkbox.checked = storedStatus; // Set the checkbox checked status
        });

    </script>
    '''

    # DNS
    dns_changes_template = '''
                    <p class="cat-title">
                        <span class="category">Přehled neběžících závodníků a závodnic</span>
                    </p>
                    <table id='dataDNS'>                        
                        {table_data}
                    </table>
                '''
    dns_changes_data = ''
    if len(changes['dns']) == 0:
        dns_changes_data += '''
        <tr>        
            <td class='nodata' colspan='4'>Žadní neběžící závodníci a závodnice.</td>
        </tr>
        '''
    else:
        dns_changes_data += '''
                <tr>
                    <!-- <th class='id'>Id</th> -->
                    <th onclick="sortTable(0, 'dataDNS')" class='solved'>Vyřešeno</th>
                    <th onclick="sortTable(1, 'dataDNS')" class='timestamp'>Čas změny</th>
                    <th onclick="sortTable(2, 'dataDNS')" class='name'>Jméno</th>
                    <th onclick="sortTable(3, 'dataDNS')" class='club'>Klub</th>
                    <th onclick="sortTable(4, 'dataDNS')" class='card'>Čip</th>
                </tr>
                '''
        for dns in changes['dns']:
            dns_changes_data += '''            
            <tr id='''+dns[0]+'''>
                <!-- <td class='id'>'''+dns[0]+'''</td> -->
                <!-- <td class='timestamp'>'''+dns[1].strftime('%d.%m.%Y %H:%M:%S')+'''</td> -->
                <td><input type="checkbox" class="solved"></td>
                <td class='timestamp'>'''+dns[1].strftime('%H:%M:%S')+'''</td>
                <td class='name'>'''+dns[2]+'''</td>
                <td class='club'>'''+dns[3]+'''</td>
                <td class='card'>'''+str(dns[4])+'''</td>
            </tr>
            '''

    dns_changes_html = dns_changes_template.format(table_data=dns_changes_data)

    # Cards
    cards_changes_template = '''
                    <p class="cat-title">
                        <span class="category">Přehled změn čipů</span>
                    </p>
                    <table id='dataCards'>                        
                        {table_data}
                    </table>
                '''
    cards_changes_data = ''
    if len(changes['changed_cards']) == 0:
        cards_changes_data += '''
        <tr>
            <td class='nodata' colspan='5'>Žadné změny čipů.</td>
        </tr>
        '''
    else:
        cards_changes_data += '''
                <tr>
                    <!-- <th class='id'>Id</th> -->
                    <th onclick="sortTable(0, 'dataCards')" class='solved'>Vyřešeno</th>
                    <th onclick="sortTable(1, 'dataCards')" class='timestamp'>Čas změny</th>
                    <th onclick="sortTable(2, 'dataCards')" class='name'>Jméno</th>
                    <th onclick="sortTable(3, 'dataCards')" class='club'>Klub</th>
                    <th onclick="sortTable(4, 'dataCards')" class='oldcard'>Starý čip</th>
                    <th onclick="sortTable(5, 'dataCards')" class='card'>Nový čip</th>
                </tr>
                '''
        for card in changes['changed_cards']:
            cards_changes_data += '''            
            <tr id='''+card[0]+'''>
                <!-- <td class='id'>'''+card[0]+'''</td> -->
                <td><input type="checkbox" class="solved"></td>
                <td class='timestamp'>'''+card[1].strftime('%H:%M:%S')+''' </td>
                <td class='name'>'''+card[2]+'''</td>
                <td class='club'>'''+card[3]+'''</td>
                <td class='oldcard'>'''+str(card[4])+'''</td>
                <td class='card'>'''+str(card[5])+'''</td>
            </tr>
            '''

    cards_changes_html = cards_changes_template.format(table_data=cards_changes_data)

    # Late starts
    late_starts_changes_template = '''
                    <p class="cat-title">
                        <span class="category">Přehled opožděných startů</span>
                    </p>
                    <table id='dataLateStart'>                        
                        {table_data}                        
                    </table>
                '''
    late_starts_changes_data = ''
    if len(changes['late_starts']) == 0:
        late_starts_changes_data += '''
        <tr>
            <td class='nodata' colspan='4'>Žadné opožděné starty.</td>
        </tr>
        '''
    else:
        late_starts_changes_data += '''
                <tr>
                    <!-- <th class='id'>Id</th> -->
                    <th onclick="sortTable(0, 'dataLateStart')" class='solved'>Vyřešeno</th>
                    <th onclick="sortTable(1, 'dataLateStart')" class='timestamp'>Čas změny</th>
                    <th onclick="sortTable(2, 'dataLateStart')" class='name'>Jméno</th>
                    <th onclick="sortTable(3, 'dataLateStart')" class='club'>Klub</th>
                    <th onclick="sortTable(4, 'dataLateStart')" class='card'>Čip</th>
                </tr>
                '''
        for late_start in changes['late_starts']:
            print('Row:', late_start, ', timestamp:', late_start[1])
            # <td class='timestamp'>'''+late_start[1].strftime('%H:%M:%S')+'''</td>
            late_starts_changes_data += '''            
            <tr id='''+late_start[0]+'''>
                <!-- <td class='id'>'''+late_start[0]+'''</td> -->
                <td><input type="checkbox" class="solved"></td>
                <td class='timestamp'>'''+format_timestamp(late_start[1])+'''</td>
                <td class='name'>'''+late_start[2]+'''</td>
                <td class='club'>'''+late_start[3]+'''</td>
                <td class='card'>'''+str(late_start[4])+'''</td>
            </tr>
            '''

    late_starts_changes_html = late_starts_changes_template.format(table_data=late_starts_changes_data)

    # Comments
    comments_changes_template = '''
                    <p class="cat-title">
                        <span class="category">Přehled komentářů od startérů</span>
                    </p>
                    <table id='dataComments'>              
                        {table_data}  
                    </table>
                '''
    comments_changes_data = ''
    if len(changes['comments']) == 0:
        comments_changes_data += '''
        <tr>
            <td class='nodata' colspan='5'>Žádné nové komentáře.</td>
        </tr>
        '''
    else:
        comments_changes_data += '''
                <tr>
                    <!-- <th class='id'>Id</th> -->
                    <th onclick="sortTable(0, 'dataComments')" class='solved'>Vyřešeno</th>
                    <th onclick="sortTable(1, 'dataComments')" class='timestamp'>Čas změny</th>
                    <th onclick="sortTable(2, 'dataComments')" class='name'>Jméno</th>
                    <th onclick="sortTable(3, 'dataComments')" class='club'>Klub</th>
                    <th onclick="sortTable(4, 'dataComments')" class='card'>Čip</th>
                    <th onclick="sortTable(5, 'dataComments')" class='comment'>Komentář</th>
                </tr> 
                '''
        for comment in changes['comments']:
            comments_changes_data += '''            
            <tr id='''+comment[0]+'''>
                <!-- <td class='id'>''' + comment[0] + '''</td> -->
                <td><input type="checkbox" class="solved"></td>
                <td class='timestamp'>''' + comment[1].strftime('%H:%M:%S') + '''</td>
                <td class='name'>'''+comment[2]+'''</td>
                <td class='club'>'''+comment[3]+'''</td>
                <td class='card'>'''+str(comment[4])+'''</td>
                <td class='comment'>'''+comment[5]+'''</td>
            </tr>
            '''

    comments_changes_html = comments_changes_template.format(table_data=comments_changes_data)

    html_file = html_file_template.format(style=html_style,
                                          javascript=html_javascript,
                                          heading='O Checklist report',
                                          creator=changes['creator'],
                                          time_stamp=changes['timestamp'],
                                          content_dns=dns_changes_html,
                                          content_cards=cards_changes_html,
                                          content_late_start=late_starts_changes_html,
                                          content_comments=comments_changes_html)
    # Write the HTML to a file
    with open("report.html", "w", encoding='utf-8') as f:
        f.write(html_file)

    return html_file

def create_db_changes(changes):
    """
    Create changes that come from the start in quickevent database
    :param changes: list of changes to proceed
    """
    # Configure the logging module
    logging.basicConfig(filename='mylog.log', level=logging.INFO)

    # Establish a connection to the PostgreSQL database using the db_config dictionary
    conn = psycopg2.connect(**quickevent_db_config)

    # Create a cursor object to execute SQL commands
    cur = conn.cursor()

    # Define the INSERT command with placeholders for the values to be inserted
    insert_command = "INSERT INTO your_table_name (column1, column2, column3) VALUES (%s, %s, %s)"

    # Define the values to be inserted into the table
    values = ('value1', 'value2', 'value3')

    # Execute the INSERT command with the values
    cur.execute(insert_command, values)

    # Log the executed command to the log file
    logging.info(f"Executed command: {cur.query.decode('utf-8')}")

    # Commit the transaction to the database
    conn.commit()

    # Close the cursor and connection
    cur.close()
    conn.close()

def parse_args() -> Tuple[int, str]:
    """
    Parse input arguments
    """
    if len(sys.argv) != 3:
        program = sys.argv[0]
        print(f"Usage: {program} <config.py> <qe_event_id>", file=sys.stderr)
        sys.exit(1)
    return sys.argv[1], sys.argv[2]

if __name__ == "__main__":
    main()
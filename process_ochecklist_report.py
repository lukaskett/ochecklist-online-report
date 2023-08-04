import sys
import ftplib
import yaml
from typing import Tuple
from io import StringIO
from config import ftp_server_credentials
from datetime import datetime

"""
Process report from the mobile app O-checklist and create html report with changes that can be ticked as done
Usage: All orienteering events with startlist in iof-xml v3.0
"""

def main() -> None:
    downloaded_file = download_file_from_ftp(**ftp_server_credentials)
    changes = process_downloaded_yaml(downloaded_file)
    generate_html_report(changes)

def download_file_from_ftp(server, login, password, subfolder='/'):
    """
    Get file from ftp server
    :param server: ftp server
    :param login: Username
    :param password: password
    :param subfolder: downloaded file location
    :return: list of list wirh filename and downloaded file content
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
        downloaded_files.append([filename, downloaded_file.getvalue()])

    # Close the FTP connection
    ftp.quit()

    return downloaded_files

def process_downloaded_yaml(downloaded_files):
    """
    Iterates over all downloaded file and separates changes - dns, late starts, changes cards and new comments
    :param downloaded_files: list of lists with filename and contents of downloaded yaml files
    :return: dictionary of lists with changes by type
    """

    # Results storage
    started_ok = []
    changes_cards = []
    changes_dns = []
    changes_late_start = []
    changes_comments = []
    changes_statistics = []

    changes = {}

    for file in downloaded_files:
        # Load the contents of the downloaded YAML file
        downloaded_data = yaml.safe_load(file[1])

        # Access report data
        report_data = downloaded_data['Data']
        for runner in report_data:
            # Values
            runner_id = runner['Runner']['Id'] if runner['Runner']['Id'] is not None else ''
            runner_start_time = runner['Runner']['StartTime']
            runner_class_name = runner['Runner']['ClassName']
            runner_name = runner['Runner']['Name'] if runner['Runner']['Name'] is not None else ''
            runner_club = runner['Runner']['Org'] if runner['Runner']['Org'] is not None else ''
            runner_card = runner['Runner']['Card'] if runner['Runner']['Card'] is not None else ''

            if runner['ChangeLog'] is not None:
                # New card
                if 'NewCard' in runner['Runner']:
                    changes_cards.append([
                        runner_id,
                        runner_start_time,
                        runner['ChangeLog']['NewCard'],
                        runner_name,
                        runner_class_name,
                        runner_club,
                        runner_card,
                        runner['Runner']['NewCard']
                    ])
                # # DNS
                if 'DNS' in runner['Runner']['StartStatus']:
                    changes_dns.append([
                        runner_id,
                        runner_start_time,
                        runner['ChangeLog']['DNS'],
                        runner_name,
                        runner_class_name,
                        runner_club,
                        runner_card
                    ])
                # # Late start
                if 'Late start' in runner['Runner']['StartStatus']:
                    changes_late_start.append([
                        runner_id,
                        runner_start_time,
                        runner['ChangeLog']['LateStart'],
                        runner_name,
                        runner_class_name,
                        runner_club,
                        runner_card
                    ])
                # # Comment
                if 'Comment' in runner['Runner']:
                    changes_comments.append([
                        runner_id,
                        runner_start_time,
                        runner['ChangeLog']['Comment'],
                        runner_name,
                        runner_class_name,
                        runner_club,
                        runner_card,
                        runner['Runner']['Comment']
                    ])

            # Store started runners
            else:
                started_ok.append(runner_name + ', ' + runner_class_name + ', ' + runner_club)
        # Store statistics
        stats = {'ok': len(started_ok),
                 'dns': len(changes_dns),
                 'card-changes': len(changes_cards),
                 'late-starts': len(changes_late_start),
                 'comments': len(changes_comments)}
        changes_statistics.append([file[0], downloaded_data['Created'], downloaded_data['Creator'], downloaded_data['Version'], stats]);

    # Store into the main dictionary
    changes['dns'] = changes_dns
    changes['changed_cards'] = changes_cards
    changes['late_starts'] = changes_late_start
    changes['comments'] = changes_comments
    changes['statistics'] = changes_statistics

    # Print statistics
    print(f"Event statistics:\n"
          f"- started runners: {len(started_ok)}\n"
          f"- dns: {len(changes_dns)}\n"
          f"- cards changes: {len(changes_cards)}\n"
          f"- late starts: {len(changes_late_start)}\n"
          f"- new comments: {len(changes_comments)}")

    return changes

def generate_html_report(changes, report_name = 'online-report'):
    """
    Create html report with changes from the start in hrml format which is more readable.
    :param changes:
    :return: html_file
    """

    html_file_template = '''
        <!DOCTYPE html>
        <html>
            <head>
                <meta name="description" content="Report with changes from the start of orienteering event">
                <meta name="keywords" content="ochecklist, orienteering, start, report">
                <meta name="author" content="Lukas Kettner">
                <meta http-equiv='Content-Type' content='text/html; charset=utf-8' />
                <meta name="viewport" content="width=device-width, initial-scale=1.0" /> 
                <!-- TODO: Can be used instead of live-server -->
                <!--<meta http-equiv="refresh" content="30"> -->           
                {style}                
                <title>{heading}</title>
            </head>
            <body onload="sortTable(0, 'dataDNS'),sortTable(0, 'dataCards'),sortTable(0, 'dataLateStart'),sortTable(0, 'dataComments'),sortTable(0, 'dataStatistics')">
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
                
                <!-- Statistiky -->
                <section>{content_statistics}</section>

                <footer>
                    <p>Created with script by Cáš based on report from O Checklist mobile app.</p>
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
                    <th onclick="sortTable(1, 'dataDNS')" class='timestamp'>Star. čas</th>
                    <th onclick="sortTable(2, 'dataDNS')" class='timestamp'>Čas změny</th>
                    <th onclick="sortTable(3, 'dataDNS')" class='name'>Jméno</th>
                    <th onclick="sortTable(4, 'dataDNS')" class='class'>Kategorie</th>
                    <th onclick="sortTable(5, 'dataDNS')" class='club'>Klub</th>
                    <th onclick="sortTable(6, 'dataDNS')" class='card'>Čip</th>
                </tr>
                '''
        for dns in changes['dns']:
            dns_changes_data += '''            
            <tr id='''+dns[1].strftime('%Y%m%d%H%M%S')+dns[4]+'''>
                <!-- <td class='id'>'''+dns[0]+'''</td> -->
                <td><input type="checkbox" class="solved"></td>
                <td class='starttime'>'''+dns[1].strftime('%H:%M:%S')+'''</td>
                <td class='timestamp'>'''+dns[2].strftime('%H:%M:%S')+'''</td>
                <td class='name'>'''+dns[3]+'''</td>
                <td class='class'>'''+dns[4]+'''</td>
                <td class='club'>'''+dns[5]+'''</td>
                <td class='card'>'''+str(dns[6])+'''</td>
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
                    <th onclick="sortTable(1, 'dataCards')" class='starttime'>Star. čas</th>
                    <th onclick="sortTable(2, 'dataCards')" class='timestamp'>Čas změny</th>
                    <th onclick="sortTable(3, 'dataCards')" class='name'>Jméno</th>
                    <th onclick="sortTable(4, 'dataCards')" class='class'>Kategorie</th>
                    <th onclick="sortTable(5, 'dataCards')" class='club'>Klub</th>
                    <th onclick="sortTable(6, 'dataCards')" class='oldcard'>Starý čip</th>
                    <th onclick="sortTable(7, 'dataCards')" class='card'>Nový čip</th>
                </tr>
                '''
        for card in changes['changed_cards']:
            cards_changes_data += '''            
            <tr id='''+card[1].strftime('%Y%m%d%H%M%S')+card[4]+'''>
                <!-- <td class='id'>'''+card[0]+'''</td> -->
                <td><input type="checkbox" class="solved"></td>
                <td class='starttime'>'''+card[1].strftime('%H:%M:%S')+''' </td>
                <td class='timestamp'>'''+card[2].strftime('%H:%M:%S')+''' </td>
                <td class='name'>'''+card[3]+'''</td>
                <td class='class'>'''+card[4]+'''</td>
                <td class='club'>'''+card[5]+'''</td>
                <td class='oldcard'>'''+str(card[6])+'''</td>
                <td class='card'>'''+str(card[7])+'''</td>
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
                    <th onclick="sortTable(1, 'dataLateStart')" class='starttime'>Star. čas</th>
                    <th onclick="sortTable(2, 'dataLateStart')" class='timestamp'>Čas změny</th>
                    <th onclick="sortTable(3, 'dataLateStart')" class='name'>Jméno</th>
                    <th onclick="sortTable(4, 'dataLateStart')" class='class'>Kategorie</th>
                    <th onclick="sortTable(5, 'dataLateStart')" class='club'>Klub</th>
                    <th onclick="sortTable(6, 'dataLateStart')" class='card'>Čip</th>
                </tr>
                '''
        for late_start in changes['late_starts']:
            late_starts_changes_data += '''            
            <tr id='''+late_start[1].strftime('%Y%m%d%H%M%S')+late_start[4]+'''>
                <!-- <td class='id'>'''+late_start[0]+'''</td> -->
                <td><input type="checkbox" class="solved"></td>
                <td class='starttime'>'''+late_start[1].strftime('%H:%M:%S')+'''</td>
                <td class='timestamp'>'''+late_start[2].strftime('%H:%M:%S')+'''</td>
                <td class='name'>'''+late_start[3]+'''</td>
                <td class='class'>'''+late_start[4]+'''</td>
                <td class='club'>'''+late_start[5]+'''</td>
                <td class='card'>'''+str(late_start[6])+'''</td>
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
                    <th onclick="sortTable(1, 'dataComments')" class='starttime'>Star. čas</th>
                    <th onclick="sortTable(2, 'dataComments')" class='timestamp'>Čas změny</th>
                    <th onclick="sortTable(3, 'dataComments')" class='name'>Jméno</th>
                    <th onclick="sortTable(4, 'dataComments')" class='class'>Kategorie</th>
                    <th onclick="sortTable(5, 'dataComments')" class='club'>Klub</th>
                    <th onclick="sortTable(6, 'dataComments')" class='card'>Čip</th>
                    <th onclick="sortTable(7, 'dataComments')" class='comment'>Komentář</th>
                </tr> 
                '''
        for comment in changes['comments']:
            comments_changes_data += '''            
            <tr id='''+comment[1].strftime('%Y%m%d%H%M%S')+comment[4]+'''>
                <!-- <td class='id'>''' + comment[0] + '''</td> -->
                <td><input type="checkbox" class="solved"></td>
                <td class='starttime'>''' + comment[1].strftime('%H:%M:%S') + '''</td>
                <td class='timestamp'>''' + comment[2].strftime('%H:%M:%S') + '''</td>
                <td class='name'>'''+comment[3]+'''</td>
                <td class='class'>'''+comment[4]+'''</td>
                <td class='club'>'''+comment[5]+'''</td>
                <td class='card'>'''+str(comment[6])+'''</td>
                <td class='comment'>'''+comment[7]+'''</td>
            </tr>
            '''
    comments_changes_html = comments_changes_template.format(table_data=comments_changes_data)

    # Statistics
    statistics_changes_template = '''
                        <p class="cat-title">
                            <span class="category">Statistiky reportů</span>
                        </p>
                        <table id='dataStatistics'>              
                            {table_data}  
                        </table>
                    '''
    statistics_changes_data = ''
    if len(changes['statistics']) == 0:
        comments_changes_data += '''
        <tr>
            <td class='nodata' colspan='5'>Žádné statistiky.</td>
        </tr>
        '''
    else:
        statistics_changes_data += '''
                <tr>
                    <th onclick="sortTable(0, 'dataStatistics')" class='filename'>Název souboru</th>
                    <th onclick="sortTable(1, 'dataStatistics')" class='created'>Datum vytvoření</th>
                    <th onclick="sortTable(2, 'dataStatistics')" class='creator'>Verze aplikace</th>
                    <th onclick="sortTable(3, 'dataStatistics')" class='version'>Verze reportu</th>
                    <th onclick="sortTable(4, 'dataStatistics')" class='ok'>OK</th>
                    <th onclick="sortTable(5, 'dataStatistics')" class='dns'>DNS</th>
                    <th onclick="sortTable(6, 'dataStatistics')" class='new-cards'>New cards</th>
                    <th onclick="sortTable(7, 'dataStatistics')" class='late-starts'>Late starts</th>
                    <th onclick="sortTable(8, 'dataStatistics')" class='new-comments'>New comments</th>
                </tr> 
                '''
        for i in range(0,len(changes['statistics'])):
            if i == 0:
                statistics_changes_data += '''            
                <tr>
                    <td class='file'>''' + changes['statistics'][i][0] + '''</td>
                    <td class='created'>'''+changes['statistics'][i][1].strftime('%H:%M:%S')+'''</td>
                    <td class='creator'>'''+changes['statistics'][i][2]+'''</td>
                    <td class='version'>'''+str(changes['statistics'][i][3])+'''</td>
                    <td class='ok'>'''+str(changes['statistics'][i][4]['ok'])+'''</td>
                    <td class='dns'>'''+str(changes['statistics'][i][4]['dns'])+'''</td>
                    <td class='new-cards'>'''+str(changes['statistics'][i][4]['card-changes'])+'''</td>
                    <td class='late-starts'>'''+str(changes['statistics'][i][4]['late-starts'])+'''</td>
                    <td class='new-comments'>'''+str(changes['statistics'][i][4]['comments'])+'''</td>
                </tr>
                '''
            else:
                statistics_changes_data += '''            
                <tr>
                    <td class='file'>''' + changes['statistics'][i][0] + '''</td>
                    <td class='created'>''' + changes['statistics'][i][1].strftime('%H:%M:%S') + '''</td>
                    <td class='creator'>''' + changes['statistics'][i][2] + '''</td>
                    <td class='version'>''' + str(changes['statistics'][i][3]) + '''</td>
                    <td class='ok'>''' + str(changes['statistics'][i][4]['ok']-changes['statistics'][i-1][4]['ok']) + '''</td>
                    <td class='dns'>''' + str(changes['statistics'][i][4]['dns']-changes['statistics'][i-1][4]['dns']) + '''</td>
                    <td class='new-cards'>''' + str(changes['statistics'][i][4]['card-changes']-changes['statistics'][i-1][4]['card-changes']) + '''</td>
                    <td class='late-starts'>''' + str(changes['statistics'][i][4]['late-starts']-changes['statistics'][i-1][4]['late-starts']) + '''</td>
                    <td class='new-comments'>''' + str(changes['statistics'][i][4]['comments']-changes['statistics'][i-1][4]['comments']) + '''</td>
                </tr>
                '''
    statistics_changes_html = statistics_changes_template.format(table_data=statistics_changes_data)

    # Generate html report
    html_file = html_file_template.format(style=html_style,
                                          javascript=html_javascript,
                                          heading='O Checklist report',
                                          time_stamp=datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
                                          content_dns=dns_changes_html,
                                          content_cards=cards_changes_html,
                                          content_late_start=late_starts_changes_html,
                                          content_comments=comments_changes_html,
                                          content_statistics=statistics_changes_html)
    # Write the HTML to a file
    with open(report_name+".html", "w", encoding='utf-8') as f:
        f.write(html_file)

    return html_file

# Not used yet, under development
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
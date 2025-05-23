import streamlit as st
import json
import uuid
from datetime import datetime, timedelta
import logging
import base64
import plotly.express as px
import pandas as pd
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import folium
from streamlit_folium import folium_static
import requests

# Constants
EVENTS_FILE = 'events.json'
REGISTRATIONS_FILE = 'registrations.json'
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin123"  # In production, use hashed passwords

# Email templates at the top level
REGISTRATION_TEMPLATE = """
Thank you for registering for {{event_name}}!

Event Details:
📅 Date: {{event_date}}
⏰ Time: {{event_time}}
📍 Location: {{event_location}}

We look forward to seeing you there!

Best regards,
Event Management Team
"""

REMINDER_TEMPLATE = """
Reminder: {{event_name}} is tomorrow!

Don't forget about the event tomorrow:
📅 Date: {{event_date}}
⏰ Time: {{event_time}}
📍 Location: {{event_location}}

See you there!

Best regards,
Event Management Team
"""

def schedule_reminder(event_id, event_data):
    """Schedule a reminder email for an event"""
    try:
        event_date = datetime.strptime(event_data['date'], '%Y-%m-%d')
        reminder_date = event_date - timedelta(days=1)
        
        # Send reminder email to all registered participants
        for registration in registrations.values():
            if registration['event_id'] == event_id:
                send_templated_email(
                    REMINDER_TEMPLATE,
                    registration['email'],
                    event_name=event_data['name'],
                    event_date=event_data['date'],
                    event_time=event_data.get('time', 'TBD'),
                    event_location=event_data.get('location', 'TBD')
                )
        return True
    except Exception as e:
        logging.error(f"Failed to schedule reminder: {str(e)}")
        return False

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Utility functions
def load_json(filename):
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"File {filename} not found. Creating new.")
        return {}
    except json.JSONDecodeError:
        logging.error(f"Invalid JSON in {filename}")
        return {}

def save_json(data, filename):
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=4)
        return True
    except Exception as e:
        logging.error(f"Failed to save {filename}: {str(e)}")
        return False

def get_event_participants(event_id):
    return [r for r in registrations.values() if r['event_id'] == event_id]

def send_registration_email(recipient_email, event_name, event_date, event_time, event_location):
    try:
        # Email configuration
        sender_email = "your-email@gmail.com"  # Replace with your email
        password = "your-app-password"  # Replace with your app password
        
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = f"Registration Confirmation - {event_name}"
        
        # Email body
        body = f"""
        Thank you for registering for {event_name}!
        
        Event Details:
        📅 Date: {event_date}
        ⏰ Time: {event_time}
        📍 Location: {event_location}
        
        We look forward to seeing you there!
        
        Best regards,
        Event Management Team
        """
        
        message.attach(MIMEText(body, "plain"))
        
        # Create SMTP session
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        return False

def delete_event(event_id):
    try:
        # Delete the event
        if event_id in events:
            del events[event_id]
            # Delete all registrations for this event
            global registrations
            registrations = {k: v for k, v in registrations.items() if v['event_id'] != event_id}
            # Save changes
            return save_json(events, EVENTS_FILE) and save_json(registrations, REGISTRATIONS_FILE)
    except Exception as e:
        logging.error(f"Failed to delete event: {str(e)}")
        return False
    return False

def get_location_coordinates(location):
    """Get coordinates for a location using OpenStreetMap Nominatim API"""
    try:
        url = f"https://nominatim.openstreetmap.org/search?q={location}&format=json"
        response = requests.get(url)
        data = response.json()
        if data:
            return float(data[0]['lat']), float(data[0]['lon'])
        return None
    except Exception as e:
        logging.error(f"Failed to get coordinates: {str(e)}")
        return None

def send_templated_email(template_str, recipient_email, **kwargs):
    """Send templated email using provided template and kwargs"""
    try:
        template = Template(template_str)
        body = template.render(**kwargs)

        # Email configuration
        sender_email = "your-email@gmail.com"  # Replace with your email
        password = "your-app-password"  # Replace with your app password
        
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = recipient_email
        message["Subject"] = f"Event Notification - {kwargs.get('event_name', '')}"
        message.attach(MIMEText(body, "plain"))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(message)
        return True
    except Exception as e:
        logging.error(f"Failed to send templated email: {str(e)}")
        return False

def display_location_map(location):
    """Create and display a map for the given location with error handling"""
    try:
        coords = get_location_coordinates(location)
        if coords:
            m = folium.Map(location=coords, zoom_start=15)
            folium.Marker(
                coords,
                popup=location,
                icon=folium.Icon(color='red', icon='info-sign')
            ).add_to(m)
            return m
    except Exception as e:
        logging.error(f"Failed to create map: {str(e)}")
    return None

def safe_rerun():
    """Safely handle page rerun with improved context checking"""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        if get_script_run_ctx():
            st.rerun()
        else:
            logging.debug("No script context found, using fallback rerun")
            try:
                st.experimental_rerun()
            except:
                st.empty()  # Create empty placeholder to trigger refresh
                logging.info("Manual refresh required")
    except Exception as e:
        logging.warning(f"Rerun failed: {str(e)}. Please refresh the page manually.")

def show_participants_modal(event_name, participants):
    """Display participants in a more organized way"""
    if st.button(f"👥 View Participants ({len(participants)})", key=f"view_part_{event_name}"):
        st.markdown(f"### Participants for {event_name}")
        if participants:
            for p in participants:
                st.markdown(f"""
                * **Name:** {p['name']}
                * **Email:** {p['email']}
                * **Phone:** {p.get('phone', 'Not provided')}
                ---
                """)
        else:
            st.info("No participants registered yet")

# Initialize data
events = load_json(EVENTS_FILE)
registrations = load_json(REGISTRATIONS_FILE)

# Modified styling function
def add_bg_from_local(image_file):
    try:
        with open(image_file, "rb") as f:
            encoded_string = base64.b64encode(f.read()).decode()
            return f"""
            <style>
            .stApp {{
                background-color: #000000;
                color: #FFFFFF;
            }}
            .main-title {{
                text-align: center;
                padding: 0;
                margin: 0;
            }}
            .stApp > header {{
                background-color: #000000;
            }}
            div.stForm {{
                background-color: #1a1a1a;
                padding: 20px;
                border-radius: 5px;
            }}
            div.element-container:empty {{
                padding: 0 !important;
                margin: 0 !important;
            }}
            .stButton button {{
                background-color: #333333;
                color: white;
                border: 1px solid #444444;
            }}
            .stTextInput input {{
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #333333;
            }}
            .stSelectbox select {{
                background-color: #1a1a1a;
                color: white;
            }}
            .sidebar-header {{
                text-align: center;
                padding: 20px 0;
                border-bottom: 1px solid #333;
                margin-bottom: 20px;
            }}
            
            .sidebar-menu {{
                display: flex;
                flex-direction: column;
                gap: 10px;
                padding: 10px;
            }}
            
            .sidebar-menu button {{
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #333;
                padding: 10px;
                border-radius: 5px;
                width: 100%;
                text-align: left;
                transition: background-color 0.3s;
            }}
            
            .sidebar-menu button:hover {{
                background-color: #333;
            }}
            
            .sidebar-menu button.active {{
                background-color: #444;
                border-color: #666;
            }}
            </style>
            """
    except FileNotFoundError:
        return """
        <style>
        .stApp {
            background-color: #000000;
            color: #FFFFFF;
        }
        </style>
        """

# Add authentication function
def authenticate(username, password):
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

# Streamlit UI setup
st.set_page_config(page_title="Event Management System", layout="centered")
st.markdown(add_bg_from_local('wd.jpg'), unsafe_allow_html=True)

# Login Screen
if not st.session_state.authenticated:
    st.markdown('<div class="main-title"><h1>Event Management System</h1></div>', unsafe_allow_html=True)
    st.markdown("### Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            if authenticate(username, password):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid username or password")
else:
    # Main Application - only shown when authenticated
    st.markdown('<div class="main-title"><h1>Event Management System</h1></div>', unsafe_allow_html=True)
    
    # Sidebar header and static menu
    st.sidebar.markdown('<div class="sidebar-header"><h2>Event Scheduler and<br>Registration System</h2></div>', unsafe_allow_html=True)
    
    menu_options = ["Create Event", "View Events", "Register for Event", "Event Dashboard", "Analytics", "Logout"]
    
    # Initialize session state for active menu if not exists
    if 'active_menu' not in st.session_state:
        st.session_state.active_menu = menu_options[0]
    
    # Create static menu buttons
    st.sidebar.markdown('<div class="sidebar-menu">', unsafe_allow_html=True)
    for option in menu_options:
        button_class = "active" if st.session_state.active_menu == option else ""
        if st.sidebar.button(option, key=f"menu_{option}", 
                           help=f"Go to {option}", 
                           use_container_width=True):
            st.session_state.active_menu = option
            if option == "Logout":
                st.session_state.authenticated = False
                st.rerun()
    st.sidebar.markdown('</div>', unsafe_allow_html=True)
    
    # Use the active menu selection
    choice = st.session_state.active_menu
    
    # Event Creation
    if choice == "Create Event":
        st.header("Create New Event")
        with st.form("event_creation"):
            name = st.text_input("Event Name")
            desc = st.text_area("Description")
            date = st.date_input("Event Date")
            time = st.time_input("Event Time")
            capacity = st.number_input("Max Capacity", min_value=1)
            location = st.text_input("Event Location")
            
            submit = st.form_submit_button("Create Event")
            if submit:
                try:
                    if not name or not desc or not location:
                        raise ValueError("Name, description and location are required")

                    event_id = str(uuid.uuid4())
                    event_data = {
                        "name": name,
                        "desc": desc,
                        "date": str(date),
                        "time": str(time),
                        "location": location,
                        "capacity": capacity,
                        "registered": 0,
                        "created_at": str(datetime.now())
                    }
                    
                    events[event_id] = event_data
                    if save_json(events, EVENTS_FILE):
                        # Schedule reminder only if event save was successful
                        if schedule_reminder(event_id, event_data):
                            st.success(f"🎉 Event '{name}' has been created with reminder!")
                        else:
                            st.success(f"🎉 Event '{name}' has been created! (Reminder setup failed)")
                        st.balloons()
                    else:
                        st.error("Failed to save event data")
                except Exception as e:
                    st.error(f"Failed to create event: {str(e)}")

    # New View Events Section
    elif choice == "View Events":
        st.header("Available Events")
        
        # Create two columns for events
        left_col, right_col = st.columns(2)
        
        # Split events into two lists for columns
        event_items = list(events.items())
        mid_point = len(event_items) // 2
        
        # Left column events
        with left_col:
            for event_id, event in event_items[:mid_point]:
                with st.expander(f"{event['name']} - {event['date']}"):
                    # Event details
                    st.write("📝 Description:", event['desc'])
                    st.write("📍 Location:", event.get('location', 'TBD'))
                    
                    # Add map for location
                    if event.get('location'):
                        try:
                            map_obj = display_location_map(event['location'])
                            if map_obj:
                                st.write("📍 Location Map:")
                                folium_static(map_obj, width=300, height=200)
                            else:
                                st.warning(f"Could not load map for {event['location']}")
                        except Exception as e:
                            st.error(f"Failed to display map: {str(e)}")
                    
                    st.write("⏰ Time:", event.get('time', 'TBD'))
                    st.write("👥 Capacity:", f"{event['registered']}/{event['capacity']}")
                    
                    participants = get_event_participants(event_id)
                    show_participants_modal(event['name'], participants)
                    
                    # Add section divider for settings
                    st.markdown("---")
                    st.markdown("### ⚙️ Other Settings")
                    
                    if st.button("🗑️ Delete Event", key=f"del_{event_id}", type="secondary", use_container_width=True):
                        if delete_event(event_id):
                            st.success(f"Event '{event['name']}' has been deleted")
                            st.rerun()
                        else:
                            st.error("Failed to delete event")
        
        # Right column events
        with right_col:
            for event_id, event in event_items[mid_point:]:
                with st.expander(f"{event['name']} - {event['date']}"):
                    # Event details
                    st.write("📝 Description:", event['desc'])
                    st.write("📍 Location:", event.get('location', 'TBD'))
                    
                    # Add map for location
                    if event.get('location'):
                        try:
                            map_obj = display_location_map(event['location'])
                            if map_obj:
                                st.write("📍 Location Map:")
                                folium_static(map_obj, width=300, height=200)
                            else:
                                st.warning(f"Could not load map for {event['location']}")
                        except Exception as e:
                            st.error(f"Failed to display map: {str(e)}")
                    
                    st.write("⏰ Time:", event.get('time', 'TBD'))
                    st.write("👥 Capacity:", f"{event['registered']}/{event['capacity']}")
                    
                    participants = get_event_participants(event_id)
                    show_participants_modal(event['name'], participants)
                    
                    # Add section divider for settings
                    st.markdown("---")
                    st.markdown("### ⚙️ Other Settings")
                    
                    if st.button("🗑️ Delete Event", key=f"del_r_{event_id}", type="secondary", use_container_width=True):
                        if delete_event(event_id):
                            st.success(f"Event '{event['name']}' has been deleted")
                            st.rerun()
                        else:
                            st.error("Failed to delete event")

    # Enhanced Registration
    elif choice == "Register for Event":
        st.header("Register for Event")
        
        # Filter out full events
        available_events = {k: v for k, v in events.items() if v['registered'] < v['capacity']}
        
        if not available_events:
            st.warning("No events available for registration")
        else:
            event_options = {v['name']: k for k, v in available_events.items()}
            
            # Use pre-selected event if coming from quick registration
            default_event = None
            if 'selected_event' in st.session_state:
                default_event = next(
                    (name for name, eid in event_options.items() 
                     if eid == st.session_state['selected_event']), 
                    None
                )
                
            selected = st.selectbox(
                "Choose Event",
                list(event_options.keys()),
                index=list(event_options.keys()).index(default_event) if default_event else 0,
                key="event_select"
            )
            
            # Clear the selected event from session after using it
            if 'selected_event' in st.session_state:
                del st.session_state['selected_event']

            # Make registration more casual
            with st.form("registration_form", clear_on_submit=True):
                st.markdown("### 🎫 Join this awesome event!")
                
                event_id = event_options[selected]
                event = events[event_id]
                
                st.markdown(f"""
                **{event['name']}**
                * 📅 When: {event['date']} at {event.get('time', 'TBD')}
                * 📍 Where: {event.get('location', 'TBD')}
                * 👥 Spots left: {event['capacity'] - event['registered']} out of {event['capacity']}
                """)
                
                name = st.text_input("👤 What's your name?")
                email = st.text_input("📧 Where can we reach you? (email)")
                phone = st.text_input("📱 Phone number (optional)")
                
                submit = st.form_submit_button("Count me in! 🎉")
                if submit:
                    if not name or not email:
                        st.error("Name and email are required")
                    else:
                        reg_id = str(uuid.uuid4())
                        registrations[reg_id] = {
                            "event_id": event_id,
                            "name": name,
                            "email": email,
                            "phone": phone,
                            "timestamp": str(datetime.now())
                        }
                        event['registered'] += 1
                        
                        # Save registration and send email
                        if save_json(events, EVENTS_FILE) and save_json(registrations, REGISTRATIONS_FILE):
                            if send_templated_email(
                                REGISTRATION_TEMPLATE,
                                email,
                                event_name=event['name'],
                                event_date=event['date'],
                                event_time=event.get('time', 'TBD'),
                                event_location=event.get('location', 'TBD')
                            ):
                                st.success(f"Successfully registered for {event['name']}! Check your email for confirmation.")
                            else:
                                st.warning(f"Registered successfully, but failed to send confirmation email.")
                            st.balloons()
                        else:
                            st.error("Failed to save registration data")

    # Dashboard
    elif choice == "Event Dashboard":
        st.header("📊 Event Participation Dashboard")
        for event_id, event in events.items():
            st.subheader(event['name'])
            st.write("📅 Date:", event['date'])
            st.write("👥 Registered:", event['registered'], "/", event['capacity'])
            st.progress(event['registered'] / event['capacity'])

    elif choice == "Analytics":
        st.header("📈 Event Analytics Dashboard")
        
        if not events:
            st.warning("No events available for analysis")
        else:
            # Create containers for layout
            metrics_container = st.container()
            col1, col2 = st.columns(2)
            
            with metrics_container:
                # Key Metrics Row
                metric1, metric2, metric3 = st.columns(3)
                
                total_events = len(events)
                total_regs = len(registrations)
                avg_fill = sum(e.get('registered', 0)/e.get('capacity', 1) for e in events.values()) / total_events if total_events else 0
                
                with metric1:
                    st.metric("Total Events", total_events)
                with metric2:
                    st.metric("Total Registrations", total_regs)
                with metric3:
                    st.metric("Average Fill Rate", f"{avg_fill*100:.1f}%")
            
            # Create DataFrame for events with default values
            events_data = [{
                'name': event['name'],
                'capacity': event.get('capacity', 0),
                'registered': event.get('registered', 0),
                'date': event.get('date', 'N/A'),
                'location': event.get('location', 'N/A')
            } for event_id, event in events.items()]
            
            events_df = pd.DataFrame(events_data)
            events_df['fill_rate'] = (events_df['registered'] / events_df['capacity'] * 100).fillna(0)
            
            with col1:
                st.subheader("Registration by Event")
                # Create bar chart for event registrations
                fig_reg = px.bar(
                    events_df,
                    x='name',
                    y='registered',
                    title='Event Registration Numbers',
                    labels={'registered': 'Registered Participants', 'name': 'Event Name'}
                )
                st.plotly_chart(fig_reg, use_container_width=True)
            
            with col2:
                st.subheader("Event Capacity Utilization")
                # Create pie chart for capacity utilization
                fig_util = px.pie(
                    events_df,
                    values='capacity',
                    names='name',
                    title='Event Capacity Distribution'
                )
                st.plotly_chart(fig_util, use_container_width=True)
            
            if registrations:
                # Registration Timeline
                st.subheader("Registration Timeline")
                reg_df = pd.DataFrame.from_dict(registrations, orient='index')
                reg_df['timestamp'] = pd.to_datetime(reg_df['timestamp'])
                reg_df = reg_df.sort_values('timestamp')
                
                fig_timeline = px.line(
                    reg_df.groupby('timestamp').size().reset_index(name='count'),
                    x='timestamp',
                    y='count',
                    title='Registration Timeline'
                )
                st.plotly_chart(fig_timeline, use_container_width=True)
                
                # Participant Details
                st.subheader("Recent Registrations")
                reg_details = pd.DataFrame.from_dict(registrations, orient='index').tail(5)
                
                # Create a new DataFrame with event names
                reg_with_events = reg_details.copy()
                reg_with_events['event_name'] = reg_with_events['event_id'].map(lambda x: events[x]['name'])
                
                # Display only specified columns
                st.dataframe(reg_with_events[['name', 'email', 'event_name', 'timestamp']])
            else:
                st.info("No registrations yet")

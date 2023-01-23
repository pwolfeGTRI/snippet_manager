# Snippet Folder Formatting

This is where events generate a folder per event along with videos from each camera that saw that event inside


## Folder Format

Example: `2023-01-23_E1_ID165_T21-55-59_T21-55-59_UTC`

For each event a folder will be created in your snippets folder of format
    
    {date_str}_E{event_type_int}_ID{primary_obj_global_id}_T{event_start_time}_T{event_end_time}_UTC

where 
- {date_str} is the date in format `%Y-%m-%d`
- {primary_obj_global_id} is the event's primary object's global_id
- {event_start_time} is a string for the full event's start time in format `%H-%M-%S`
- {event_end_time} is a string for the full event's end time in format `%H-%M-%S`


## File Format

Example: `B8A44F3C4792_2023-01-23_T21-55-59_T21-55-59_UTC.mp4`

For each camera that saw the event there will be a file of format: 

    {camera_id}_{date_str}_{start_time}_{end_time}

where
- camera_id is the upper case hex string format of the camera's mac address (no delimiters)
- {date_str} is the date in format `%Y-%m-%d`
- {start_time} is a string for camera's start time in format `%H-%M-%S`
- {end_time} is a string for camera's end time in format `%H-%M-%S`

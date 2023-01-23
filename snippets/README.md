# Snippet Folder Formatting

This is where events generate a folder per event along with videos from each camera that saw that event inside


## Folder Format

For each event a folder will be created of format

    {primary_obj_global_id}_{event_start_time}_{event_end_time}
    output_folder = /{snippets_folder}/{date_str}_E{event_type_int}_{primary_obj_global_id}_T{event_start_time}_T{event_end_time}_UTC"


where 
- primary_obj_global_id is the event's primary object's global_id
- event_start_time is a string for the full event's start time in format `'%H-%M-%SZ'`
- event_end_time is a string for the full event's end time in format `'%H-%M-%SZ'`


## File Format

For each camera that saw the event there will be a file of format: 

    camera_id start_time end_time

where
- camera_id is the upper case hex string format of the camera's mac address
- event_start_time is a string for the full event's start time in format `'%Y-%m-%dT%H-%M-%SZ'`
- event_end_time is a string for the full event's end time in format `'%Y-%m-%dT%H-%M-%SZ'`


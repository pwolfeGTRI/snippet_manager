# Snippet Folder Formatting

This is where events generate a folder per event along with videos from each camera that saw that event inside


## Event Enums for Reference

event type enums (last updated 2/1/2023). [link to msgint submodule's latest SkaiEventType enum in protobuf](../msg_interface/package/skaiproto/SkaiEventProtoMsg.proto)

        enum SkaiEvent {
            DEFAULT = 0;
            CUSTOMER_DETECTED = 1;
            CUSTOMER_NOT_GREETED = 2;
            CUSTOMER_GREETING_STARTED = 3;
            CUSTOMER_GREETING_ENDED = 4;
            EMPLOYEE_NOT_IDLE = 5;
            EMPLOYEE_IDLE = 6;
            VEHICLE_DETECTED = 7;
            VEHICLE_NOT_IDLE = 8;
            VEHICLE_IDLE = 9;
            VEHICLE_SERVICE_STARTED = 10;
            VEHICLE_SERVICE_ENDED = 11;
            TRACK_LOCATION_CHANGE = 12;
            CARWASH_BACKUP = 13;
            LICENSE_PLATE_DETECTED = 14;
        }

## Folder Format

Example: `2023-01-23/E1/ID165/T21-55-59_T21-55-59_UTC`

For each event a folder will be created in your snippets folder of format
    
    {date_str}/E{msg.event}/ID{msg.primary_obj.global_id}/T{event_start_time}_T{event_end_time}_UTC

where 
- {date_str} is the date in format `%Y-%m-%d`
- {msg.event} is the event type integer (see event enum section above)
- {msg.primary_obj.global_id} is the event's primary object's global_id
- {event_start_time} is a string for the full event's start time in format `%H-%M-%S`
- {event_end_time} is a string for the full event's end time in format `%H-%M-%S`

## File Format

Example: `B8A44F3C4792_2023-01-23_T21-55-59_T21-55-59_UTC.mp4`

For each camera that saw the event there will be a file of format: 

    {camera_id}_{date_str}_{start_time}_{end_time}

where
- {camera_id} is the upper case hex string format of the camera's mac address (no delimiters)
- {date_str} is the date in format `%Y-%m-%d`
- {start_time} is a string for camera's start time in format `%H-%M-%S`
- {end_time} is a string for camera's end time in format `%H-%M-%S`


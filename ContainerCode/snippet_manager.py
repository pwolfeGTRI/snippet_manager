from moviepy.editor import *

def join_mp4_files(file_list, output_file):
    video_clips = [VideoFileClip(f) for f in file_list]
    final_clip = concatenate_videoclips(video_clips)
    final_clip.write_videofile(output_file)

# Example usage
file_list = ["file1.mp4", "file2.mp4", "file3.mp4"]
join_mp4_files(file_list, "output.mp4")

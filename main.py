from moviepy.editor import *
from moviepy.video.fx.all import crop
import whisper

import requests
import json
from selenium import webdriver
import random

# to install everything run the command "pip install -r requirements.txt" in terminal
# you also need to install firefox into your python folder

#here are your config things
#----------------------------------------
api_key = '' # your elevenlabs api token goes here
voice_id = 'pNInz6obpgDQGcFmaJgB' # default is pNInz6obpgDQGcFmaJgB, this is the text to speech voice id

censor_text = True # default is True
loop_number = 1 # default is 1, this is the how many videos you want to make
subreddit = 'AskReddit'  # default is AskReddit, this is the reddit page you want to get the stories from
min_words = 100  # default is 100, this is the minimum length (in words) of the story 

bgd_video = 'gameplay.mp4'  # default is gameplay.mp4, this is the video that plays in the background
text_colour = 'white' # default is white, this is the color of the subtitle text
font_size = 75 # default is 75, this is the size of the subtitle text
stroke_weight = 4 # default is 4, this is the stroke size around the subtitle text
stroke_colour = 'black' # default is black, this is the stroke color around the subtitle text



def censor(input):
    bad_words = requests.get('https://raw.githubusercontent.com/snguyenthanh/better_profanity/master/better_profanity/profanity_wordlist.txt').text.split()
    words = input.lower().split()
    for input in words:
        if input in bad_words:
            words[words.index(input)] = words[words.index(input)][:1]
    return ' '.join(map(str, words))

def texttospeech(text, filename):
    ttsheaders = {
        "accept": "audio/mpeg",
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    ttsdata = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
        "stability": 0.5,
        "similarity_boost": 0.5
        }
    }

    tts = requests.post(f'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream', json=ttsdata, headers=ttsheaders, stream=True)

    with open(f'{filename}.mp3', 'wb') as f:
        for chunk in tts.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)


headers = {
    'user-agent': 'Mozilla/5.0 (Macintosh; PPC Mac OS X 10_8_7 rv:5.0; en-US) AppleWebKit/533.31.5 (KHTML, like Gecko) Version/4.0 Safari/533.31.5',
}

posts = json.loads(requests.get(f'https://www.reddit.com/r/{subreddit}.json', headers=headers).text)


def getBody(postnumber, commentnumber):
    comments = json.loads(requests.get(f'{posts["data"]["children"][postnumber]["data"]["url"]}.json', headers=headers).text)
    body = comments[1]["data"]["children"][commentnumber]["data"]["body"]
    return body


def createVideo(postnumber, commentnumber):
    title = posts["data"]["children"][postnumber]["data"]["title"]
    url = posts["data"]["children"][postnumber]["data"]["url"]
    name = posts["data"]["children"][postnumber]["data"]["name"]
    nsfw = posts["data"]["children"][postnumber]["data"]["over_18"]
    if nsfw == False:
        print(title)
        body = getBody(postnumber, commentnumber)

        commentlength = len(list(map(len, body.split())))
        
        if commentlength < min_words:
            print(f"length was {commentlength}, not long enough!")
            
            if commentnumber + 1 == 27:
                createVideo(postnumber + 1, 1)
            else:
                createVideo(postnumber, commentnumber + 1)

            return
        else:
            print(f"making video! length is {commentlength}")
            



        driver = webdriver.Firefox()
        driver.get(url)

        element = driver.find_element_by_id(f'{name}')
        scrrenshot = element.screenshot_as_png
        with open('post_title.png', 'wb') as f:
            f.write(scrrenshot)

        

        driver.quit()

        if censor_text == True:
            body = censor(body)
            title = censor(title)

        texttospeech(body,'comment')
        texttospeech(title,'output')

        titlevoice = AudioFileClip("output.mp3")
        commentvoice = AudioFileClip("comment.mp3")

        model = whisper.load_model("base")
        result = model.transcribe("comment.mp3", word_timestamps=True, verbose=True)
        segmentslength = len(result["segments"])

        print('done transcribing!')

        videolength = titlevoice.duration + commentvoice.duration + 1
        video = VideoFileClip(bgd_video)
        video = video.cutout(0, random.uniform(2,video.duration-videolength-2)).set_duration(videolength)

        (w, h) = video.size

        crop_width = h * 9/16

        x1, x2 = (w - crop_width)//2, (w+crop_width)//2
        y1, y2 = 0, h
        cropped_clip = crop(video, x1=x1, y1=y1, x2=x2, y2=y2)

        title = ImageClip("post_title.png").set_start(0).set_duration(titlevoice.duration).set_pos(("center",100)).resize(width=500) # if you need to resize...

        compositeclip = [cropped_clip, title]


        for i in range(segmentslength):
            words = result["segments"][i]["words"]
            for word in words:
                txt_clip = TextClip(word["word"], fontsize = font_size, color = text_colour, size = cropped_clip.size, method='caption', stroke_width=stroke_weight, stroke_color=stroke_colour, font="EncodeSansNarrow-Black")  

            
                duration = word["end"] - word["start"]
                        
                txt_clip = txt_clip.set_start(titlevoice.duration + word["start"]).set_pos('center').set_duration(duration)  
                compositeclip.append(txt_clip)

        

           
            
            




        final = CompositeVideoClip(compositeclip)

        audio = CompositeAudioClip([titlevoice, commentvoice.set_start(titlevoice.duration + 0.25)])

        final.audio = audio

        final.write_videofile(f'finishedvideo.mp4')
    else:
        print('post is nsfw')
        createVideo(random.randint(0,26),1)


for video in range(loop_number):
    createVideo(random.randint(0,26),1)
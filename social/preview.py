"""Offline preview of the ACTIVE renderer. Never contacts AI, Buffer or Instagram."""
import argparse
import json
from datetime import date
from pathlib import Path
from PIL import Image, ImageDraw
from social import quality, editorial, storyboard, creative, reel, worker


def generate(day, directory, count=4, reels=2, videos=True):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    rows=[];thumbnails=[]
    for i,c in enumerate(quality.daily_plan(day,count,reels)):
        is_reel=(i+1)*reels//count > i*reels//count
        out=directory/f'{i+1:02}-{c["story_format"]}';out.mkdir(exist_ok=True)
        copy=editorial.authored(c);copy['storyboard']=storyboard.plan(c)
        caption=copy['caption']+creative.caption_suffix(c)
        if is_reel:
            caption+='\n\n'+reel.music_credit(c)
            times=[0,copy['storyboard']['beats'][0]+3,copy['storyboard']['beats'][1]+1,copy['storyboard']['beats'][2]+1]
            for j,t in enumerate(times):
                frame=reel.frame(c,copy,t);frame.save(out/f'scene-{j+1}.png');thumbnails.append((frame,str(i+1)+' / '+str(j+1)))
            # The cover comes from the actual hook, not a generic branded card.
            reel.frame(c,copy,.35).save(out/'cover.png')
            if videos:reel.render(c,out,copy)
        else:
            paths=worker.render(c,copy,out)
            thumbnails.extend((Image.open(p).copy(),f'{i+1} / {j+1}') for j,p in enumerate(paths))
        (out/'caption.txt').write_text(caption)
        rows.append({'slot':i,'kind':'reel' if is_reel else 'carousel','topic':c['topic'],
                     'format':c['story_format'],'hook':copy['hook'],'destination':creative.url(c),
                     'storyboard':copy['storyboard'],'narration':'not requested; original music only'})
        print(f"Rendered {i+1}/{count}: {rows[-1]['kind']} / {c['topic']} / {c['story_format']}",flush=True)
    sheet=Image.new('RGB',(4*240,((len(thumbnails)+3)//4)*450),'#e8e3d9')
    for i,(im,label) in enumerate(thumbnails):
        im.thumbnail((240,426));x=i%4*240;y=i//4*450;sheet.paste(im,(x,y));ImageDraw.Draw(sheet).text((x+6,y+430),label,fill='#222222')
    sheet.save(directory/'contact-sheet.jpg',quality=90)
    (directory/'plan.json').write_text(json.dumps(rows,indent=2))
    return rows

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--day',default=date.today().isoformat())
    parser.add_argument('--output',default='social/output')
    parser.add_argument('--count',type=int,default=4)
    parser.add_argument('--reels',type=int,default=2)
    parser.add_argument('--stills-only',action='store_true')
    args=parser.parse_args()
    if not 1<=args.count<=12 or not 0<=args.reels<=min(5,args.count):parser.error('Use 1..12 items and 0..min(5,count) reels.')
    generate(args.day,args.output,args.count,args.reels,not args.stills_only)

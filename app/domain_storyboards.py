"""Offline, source-linked original storyboard drafts, not factual verification.

The renderer deliberately has no network, account, or publishing integration.
Source independence, claim relations, and licenses remain human declarations.
"""
from __future__ import annotations
import hashlib
import json
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .domain_adapters import POLICIES, ExternalSource


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')


class Source(ExternalSource):
    source_id: str = Field(pattern=r'^[A-Z][A-Z0-9]{0,7}$')


class Link(Strict):
    source_id: str = Field(pattern=r'^[A-Z][A-Z0-9]{0,7}$')
    relation: Literal['SUPPORTS', 'REFUTES', 'CONTEXT']
    locator: str = Field(min_length=2, max_length=160)


class Claim(Strict):
    text: str = Field(min_length=5, max_length=115)
    links: list[Link] = Field(min_length=2, max_length=6)


class Storyboard(Strict):
    domain: str
    format: Literal['SHORT', 'LONG']
    title: str = Field(min_length=6, max_length=62)
    claims: list[Claim] = Field(min_length=1, max_length=2)
    sources: list[Source] = Field(min_length=2, max_length=12)
    specialist_facts: dict[str, str]
    synthetic_demo: bool = False

    @model_validator(mode='after')
    def validate_evidence(self):
        if self.domain not in POLICIES:
            raise ValueError('unknown domain')
        if any(not self.specialist_facts.get(f, '').strip() for f in POLICIES[self.domain].specialist_fields):
            raise ValueError('domain specialist fields missing')
        # This English-only technical renderer has no font/complex-script acceptance.
        for txt in [self.title, *(c.text for c in self.claims)]:
            if not txt.strip() or not txt.isascii() or any(ord(ch)<32 for ch in txt):
                raise ValueError('printable ASCII storyboard text required')
        sources = {s.source_id: s for s in self.sources}
        if len(sources) != len(self.sources):
            raise ValueError('duplicate source ID')
        canonical = set()
        for s in self.sources:
            u = urlsplit(s.url)
            if u.scheme != 'https' or not u.hostname or u.username or u.password or u.fragment:
                raise ValueError('explicit HTTPS source URL without credentials or fragment required')
            if not s.independence_group.strip() or not s.publisher.strip():
                raise ValueError('blank source metadata')
            if u.hostname.endswith('.invalid') and not self.synthetic_demo:
                raise ValueError('synthetic domain requires demo mode')
            key = (u.hostname.lower(), u.path.rstrip('/'), u.query)
            if key in canonical:
                raise ValueError('duplicate source URL')
            canonical.add(key)
        for c in self.claims:
            if len({x.source_id for x in c.links}) != len(c.links):
                raise ValueError('duplicate claim source')
            if any(l.source_id not in sources or not l.locator.strip() for l in c.links):
                raise ValueError('unresolved claim source/locator')
            if any(l.relation == 'REFUTES' for l in c.links):
                raise ValueError('refuting evidence requires human resolution')
            supporting = [sources[l.source_id] for l in c.links if l.relation == 'SUPPORTS']
            if (len({s.independence_group.strip().casefold() for s in supporting}) < 2
                or len({urlsplit(s.url).hostname for s in supporting}) < 2
                or not any(s.record_type == 'PRIMARY' for s in supporting)):
                raise ValueError('each claim requires declared primary and independent supporting group/host')
        return self


# Original diagram primitives: no borrowed media, simulated measurements or factual plots.
GRAMMAR = {
 'newsroom': ('Chronology', 'timeline'), 'science': ('Method to evidence', 'nodes'),
 'technology': ('Versioned reproduction', 'terminal'), 'business': ('Filing review', 'table'),
 'gaming': ('Original game analysis', 'grid'), 'history': ('Archive chronology', 'timeline'),
 'space': ('Illustrative orbit - not to scale', 'orbit'), 'learning': ('Worked example', 'nodes'),
 'sports': ('Illustrative field - no live data', 'field'), 'career': ('Decision branches', 'tree'),
 'productivity': ('Process review', 'flow'), 'culture': ('Attribution trail', 'tree')}


def _font(size):
    try:
        return ImageFont.truetype('DejaVuSans.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)


def _wrap(draw, text, font, width):
    lines, line = [], ''
    for word in text.split():
        if draw.textlength(word,font=font)>width:
            raise ValueError('word exceeds storyboard safe width')
        trial = (line+' '+word).strip()
        if line and draw.textlength(trial,font=font)>width:
            lines.append(line); line=word
        else: line=trial
    return lines+[line]


def _text(draw, text, x, y, width, size, color, max_lines):
    f=_font(size); lines=_wrap(draw,text,f,width)
    if len(lines)>max_lines:
        raise ValueError('text exceeds storyboard safe area')
    for i,line in enumerate(lines):
        draw.text((x,y+i*(size+5)),line,font=f,fill=color)


def _diagram(d, box, kind):
    x,y,w,h=box; c='#74d9c6'; ink='#92accd'; fill='#20374d'
    def point(a,b):return (int(x+w*a),int(y+h*b))
    def line(a,b, color=c):d.line([point(*a),point(*b)],fill=color,width=4)
    def node(a,b):
        px,py=point(a,b);r=10;d.ellipse((px-r,py-r,px+r,py+r),fill=c)
    if kind=='timeline':
        line((.12,.50),(.88,.50));
        for a in (.18,.50,.82):node(a,.50);line((a,.32),(a,.50),ink)
    elif kind in ('nodes','flow'):
        for a in (.2,.5,.8):
            p=point(a-.10,.27);q=point(a+.10,.73);d.rounded_rectangle((*p,*q),radius=10,fill=fill,outline=c,width=3)
        line((.30,.50),(.40,.50));line((.60,.50),(.70,.50))
    elif kind=='terminal':
        d.rounded_rectangle((*point(.13,.12),*point(.87,.88)),radius=12,outline=c,width=3,fill=fill)
        for i in range(3):line((.23,.32+i*.16),(.70-i*.10,.32+i*.16),ink)
    elif kind in ('table','grid'):
        for a in range(3):
            for b in range(2):d.rectangle((*point(.18+.22*a,.18+.32*b),*point(.38+.22*a,.45+.32*b)),outline=c,width=2,fill=fill)
    elif kind=='orbit':
        d.ellipse((*point(.15,.10),*point(.85,.90)),outline=c,width=3);node(.5,.5);node(.75,.23)
    elif kind=='field':
        d.rectangle((*point(.12,.12),*point(.88,.88)),outline=c,width=3);line((.5,.12),(.5,.88));
        for a,b in ((.28,.35),(.38,.65),(.65,.32),(.76,.68)):node(a,b)
    else:
        for a in (.23,.50,.77):line((.50,.25),(a,.72));node(a,.72)
        node(.50,.25)


def render_board(spec: Storyboard, output: Path) -> dict:
    """Create a PNG and bind it to the complete source declaration; never overwrite."""
    spec=Storyboard.model_validate(spec.model_dump())
    if any(k.startswith('native_hi_') for k in spec.specialist_facts):
        raise ValueError('native Hindi declaration requires explicit native renderer')
    w,h=(720,1280) if spec.format=='SHORT' else (1280,720)
    img=Image.new('RGB',(w,h),'#101e31');d=ImageDraw.Draw(img)
    accent='#74d9c6';fg='#ecf5ff'; muted='#b4c7dc'; margin=40
    d.rectangle((0,0,w,14),fill=accent)
    d.text((margin,28),f'{spec.domain.upper()}  /  {spec.format} DRAFT',font=_font(24),fill=accent)
    _text(d,spec.title,margin,70,w-2*margin,36,fg,3 if spec.format=='SHORT' else 2)
    if spec.format=='SHORT':
        box=(margin,230,w-2*margin,310); cx,cy,cw=margin,580,w-2*margin
    else:
        box=(margin,190,540,350);cx,cy,cw=625,200,615
    label,kind=GRAMMAR[spec.domain]
    d.rounded_rectangle((box[0],box[1],box[0]+box[2],box[1]+box[3]),radius=18,fill='#172b40')
    _diagram(d,(box[0]+12,box[1]+15,box[2]-24,box[3]-78),kind)
    _text(d,label,box[0]+18,box[1]+box[3]-54,box[2]-36,20,muted,2)
    for i,c in enumerate(spec.claims):
        y=cy+i*192
        d.rounded_rectangle((cx,y,cx+cw,y+174),radius=13,fill='#20374d')
        d.text((cx+15,y+12),f'CLAIM {i+1}  /  HUMAN REVIEW',font=_font(19),fill=accent)
        _text(d,c.text,cx+15,y+43,cw-30,25,fg,3)
        _text(d,'Sources: '+', '.join(l.source_id for l in c.links),cx+15,y+140,cw-30,17,muted,1)
    d.rectangle((0,h-78,w,h),fill='#5f2a35')
    _text(d,'NOT FACT / RIGHTS CLEARED',margin,h-66,w-2*margin,24,'#ffffff',1)
    _text(d,'SYNTHETIC DEMO - NO REAL CLAIMS' if spec.synthetic_demo else 'UNVERIFIED HUMAN SOURCE DECLARATIONS',margin,h-32,w-2*margin,16,'#ffffff',1)
    output=Path(output)
    if output.suffix.lower()!='.png':raise ValueError('PNG output required')
    with output.open('xb') as f:img.save(f,format='PNG')
    return {'schema':'VIRALOS_DOMAIN_STORYBOARD_V1','domain':spec.domain,'format':spec.format,
            'dimensions':[w,h], 'input_sha256':hashlib.sha256(json.dumps(spec.model_dump(),sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
            'board_sha256':hashlib.sha256(output.read_bytes()).hexdigest(), 'diagram':kind,
            'synthetic_demo':spec.synthetic_demo,'claim_truth_verified':False,'source_independence_verified':False,
            'rights_cleared':False,'publication_eligible':False}

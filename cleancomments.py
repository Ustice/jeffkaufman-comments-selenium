import sys
import re
import os
import json
import urllib.parse

from private import INITIALS
from private import FB_SHOW_BLACKLIST_IDS
from private import FB_SHOW_BLACKLIST_NAMES

def query_params(url):
  return urllib.parse.parse_qs(urllib.parse.urlparse(url).query)

def sanitize_html_names(comment_html, raw_names):
  for raw_name in raw_names:
    if raw_name in comment_html:
      comment_html = comment_html.replace(raw_name, sanitize_name(raw_name))
  return comment_html

def sanitize_html(comment_html, raw_names):
  if not comment_html:
    return "[empty]"

  comment_html = sanitize_html_names(comment_html, raw_names)
  if "https://l.facebook.com" in comment_html:
    for fb_link in re.findall('https://l[.]facebook[.]com/l[.]php[?]u=[^"]*',
                              comment_html):
      real_link, = query_params(fb_link)['u']
      comment_html = comment_html.replace(fb_link, real_link)
  for attr in ['class', 'title', 'style', 'target', 'data-hovercard']:
    comment_html = re.sub(' ' + attr + '="[^"]*"', '', comment_html)
  return comment_html

def sanitize_name(name):
  name = INITIALS.get(name, name)
  name = name.split()[0]
  return name

def comment_id(link):
  qp = query_params(link)
  raw_comment_id, = qp['comment_id']
  cid = "fb-%s" % raw_comment_id
  if 'reply_comment_id' in qp:
    raw_reply_id, = qp['reply_comment_id']
    cid += "_" + raw_reply_id
  return cid

def clean_single(raw_comment, raw_names):
  # input format:
  #   name (needs sanitizing)
  #   null
  #   null
  #   null
  #   comment html (needs sanitizing)
  #
  # output format:
  #   first name / initials (cleaned name)
  #   link (absent)
  #   comment id (absent)
  #   comment_html
  #   timestamp (absent)
  #   children
  if not raw_comment:
    return ["unknown", "#", "unknown", "unknown", "-1", []]

  name, link, user_id, timestamp, comment_html, children = raw_comment
  if (user_id in FB_SHOW_BLACKLIST_IDS or
      name in FB_SHOW_BLACKLIST_NAMES):
    return ["opted out", "#", "unknown",
            "this user has requested that their comments not be shown here",
            timestamp, []]

  return [
    sanitize_name(name),
    "#",
    "#",
    sanitize_html(comment_html, raw_names),
    "-1",
    [clean_single(child, raw_names) for child in children]
  ]

def clean(raw_threads):
  raw_names = set()

  for raw_thread in raw_threads:
    raw_names.add(raw_thread[0])
    for raw_reply in raw_thread[-1]:
      raw_names.add(raw_reply[0])

  clean_comments = [
    clean_single(raw_thread, raw_names)
    for raw_thread in raw_threads]

  return clean_comments

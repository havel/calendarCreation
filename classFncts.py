#!/usr/bin/python

import sys
import time
import pdb

import httplib2
from apiclient.discovery import build
from apiclient.oauth import TwoLeggedOAuthCredentials
from apiclient.errors import HttpError

SLEEPY = 0

###############################
# Create a secondary calendar #
###############################
def create_cal(term, crn, title, summary, service, setTrace=False):
  import random

  if setTrace:
    pdb.set_trace()

  quota = 0 
  entry = ""

  colors = ('1', '2', '3', '4', '5', '6', '7',
            '8', '9', '10', '11', '12', '13', '14',
            '15', '16', '17', '18', '19', '20', '21',
            '22', '23', '24')

  calendar = { 
               'summary': title,
               'description' : summary,
               'location' : 'Fairbanks', 
               'timeZone': 'America/Anchorage'
             }

  for i in range(0,10):
    try:
      newCalendar = service.calendars().insert(body=calendar).execute()
    except HttpError, error:
      errorCode = error
      errorReason = errorCode.resp.reason
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      if ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"

          returnMe = "FAILED - SLEEPY = %d, i = %d\n" % (SLEEPY, i)

          return (entry, returnMe)
      elif ("Forbidden" in errorCode):
        entry = "  FAILED: FORBIDDEN"

        returnMe = "FAILED: FORBIDDEN - SLEEPY = %d, i = %d\n" % (SLEEPY, i)

        return (entry, returnMe) 
      entry = "%s | %s" % (entry, errorCode) 
      continue
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      print "** Create calendar NOT http error informaton => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      if ("invalid" in errorCode):
        entry = "  FAILED: INVALID CREDENTIALS"
        return (entry, "FAILED")
      entry = "%s | %s" % (entry, error)
      continue
    entry = "  Successfully created calendar, calId = %s\n" % newCalendar['id']
    break

  try:
    newCalendar
  except NameError:
    entry = entry + "** ERROR: %s, crn = %s - Calendar creation Failed **\n" % (title, crn)
    newCalendarId="FAILED"
    return (entry, newCalendarId) 

  newCalendarId = newCalendar['id']

  try:
    calendar_list_entry = service.calendarList().get(calendarId=newCalendarId).execute()
  except:
    exctype, error = sys.exc_info()[:2]
    errorCode = error_code_cleanup(error)
    entry = entry + "\n  color change was unsuccessful" + errorCode + "\n"
    return (entry, newCalendarId)
    
  calendar_list_entry['colorId'] = random.choice(colors)
  
  try:
    createdCalColor = service.calendarList().update(calendarId=calendar_list_entry['id'],body=calendar_list_entry).execute()
  except:
    exctype, error = sys.exc_info()[:2]
    errorCode = error_code_cleanup(error)
    entry = entry + "\n  color change was unsuccessful" + errorCode + "\n"
    createdCalColor = "FAILED"

  if (createdCalColor != "FAILED"):
    entry = entry + "  color change was successful = %s" % (calendar_list_entry['colorId'])
 
  return (entry, newCalendarId) 

#####################################################
# Set calendar permissions to public (default) read #
#####################################################
def set_permissions(calId, service, setTrace=False):
  entry = ""
  quota = 0

  if setTrace:
    pdb.set_trace()

  rule = { 
           'scope': { 
                      'type': 'default',
                    },
           'role': 'reader'
         }
  for i in range(0,10):
    try:
      returned_rule = service.acl().insert(calendarId=calId, body=rule).execute()
    except HttpError, errorCode:
      errorReason = errorCode.resp.reason
      if ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"
          return entry
      elif ("Forbidden" in errorCode):
        entry = "  FAILED: FORBIDDEN"
        return entry
      entry = "%s | %s" % (entry, errorCode)
      continue
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      print "** Create calendar NOT http error informaton => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      if ("invalid" in errorCode):
        entry = "  FAILED: INVALID CREDENTIALS"
        return entry
      entry = "%s | %s" % (entry, error)
      continue
    entry = "  Read access added to %s, %s" % (calId, returned_rule['id'])
    break

  try:
    returned_rule
  except NameError:
    entry = "** ERROR: calId = %s - NOT PUBLIC, continued to create events **\n" % (calId)

  return entry

#####################################
# Delete all events from a calendar #
#####################################
def remove_all_cal_events(calId, service, setTrace=False):
  entry = ""
  quota = 0

  if setTrace:
    pdb.set_trace()

  for i in range(0,10): 
    try:
      events = service.events().list(calendarId=calId).execute()
    except HttpError, errorCode:
      errorReason = errorCode.resp.reason
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      if ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"
          return entry
      elif ("Forbidden" in errorCode):
        entry = "  FAILED: FORBIDDEN"
        return entry
      entry = "errorCode = %s" % (errorCode)
      continue
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      print "** Create calendar NOT http error informaton => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      if ("invalid" in errorCode):
        entry = "  FAILED: INVALID CREDENTIALS"
        return entry
      entry = "%s | %s" % (entry, error)
      continue
    break

  quota = 0
  while True:
    if 'items' in events:
      for event in events['items']:
        print "  eventId = %s" % event['id']
        thisEvent = event['id']

        for i in range(0,10):
          try:
            emptyReturn = service.events().delete(calendarId=calId, eventId=thisEvent).execute()
          except HttpError, errorCode:
            errorReason = errorCode.resp.reason
            exctype, error = sys.exc_info()[:2]
            errorCode = error_code_cleanup(error) 
            print "  returned errorCode = %s" % errorCode 
            if ("Forbidden" in errorCode):
              entry = "  FAILED: FORBIDDEN"
              return entry
            elif ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
              if (quota <= 5):
                quota += 1
              else:
                entry = "  FAILED: LIMIT REACHED"
                return entry
            elif ("deleted" in errorCode):
              print "  event has already been deleted\n"
              break
            else:
              print "error => %r | %r\n" % (error, errorCode)
            entry = "%s | %s" % (entry, errorCode)
            continue
          except:
            exctype, error = sys.exc_info()[:2]
            errorCode = error_code_cleanup(error)
            print "** Create calendar NOT http error informaton => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
            if ("invalid" in errorCode):
              entry = "  FAILED: INVALID CREDENTIALS"
              return entry
            entry = "%s | %s" % (entry, error)
            continue
          break
        
      page_token = events.get('nextPageToken')
      if page_token:
        events = service.events().list(calendarId=calId, pageToken=page_token).execute()
      else:
        break
    else: 
      print "  No events"
      break

  for i in range(0,10):
    try:
      events = service.events().list(calendarId=calId).execute()
    except HttpError, errorCode:
      errorReason = errorCode.resp.reason
      print "  returned errorCode = %s" % errorCode
      if ("Forbidden" in errorCode):
        entry = "  FAILED: FORBIDDEN"
        return entry
      elif ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"
          return entry
      else:
        print "error => %r \n" % (errorCode)
      entry = "%s | %s" % (entry, errorCode)
      continue
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      print "** Create calendar listing events NOT http error informaton => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      if ("invalid" in errorCode):
        entry = "  FAILED: INVALID CREDENTIALS"
        return entry
      entry = "%s | %s" % (entry, error)
      continue
    break
    
  print "  any events left?"

  while True:
    if 'items' in events:
      for event in events['items']:
        print event
      page_token = events.get('nextPageToken')
      if page_token:
        events = service.events().list(calendarId=calId, pageToken=page_token).execute()
      else:
        break
    else:
      print "  No events"
      break

  return entry

###########################################
# Create an event to a secondary calendar #
###########################################
def create_event(meetDate, items, service, calId, dstLastYear, dstThisYear, dstNextYear, setTrace=False):
  import time
  import datetime
  from datetime import date

  if setTrace:
    pdb.set_trace()

  event = "" 
  days = ""
  meetId = "%s" % (meetDate["id"])
  startDate = meetDate["meetStartDate"]
  startTime = meetDate["startTime"]
  endTime = meetDate["endTime"]
  where = "%s %s" % (meetDate["bldg"], meetDate["rm"])

  entry = ""
  offSet = ":00.000-09:00"
  eventId = ""

  item = items.split(', ')
  course = item[0]
  term = item[1]
  crn = item[2]

  origDays ="%s%s%s%s%s%s%s" % (meetDate["sunday"], meetDate["monday"], meetDate["tuesday"], meetDate["wednesday"], meetDate["thursday"], meetDate["friday"], meetDate["saturday"])

  ########################
  # day of week starting #
  ########################
  dayofWeek = ['M', 'T', 'W', 'R', 'F', 'S', 'U']

  if (len(origDays) > 0):
    while (dayofWeek[date.weekday(startDate)] not in origDays):
      #  add one day to startDate
      startDate += datetime.timedelta(days=1) 

  if meetDate["sunday"] == "U": days = "su"
  if meetDate["monday"] =="M":
    if len(days) > 0 :  days = days + ",mo"
    else : days = days + "mo"
  if meetDate["tuesday"] =="T":
    if len(days) > 0 : days = days + ",tu"
    else :  days = days + "tu"
  if meetDate["wednesday"] =="W":
    if len(days) > 0 : days = days + ",we"
    else : days = days + "we"
  if meetDate["thursday"] =="R":
    if len(days) > 0 : days = days + ",th"
    else : days = days + "th"
  if meetDate["friday"] =="F":
    if len(days) > 0 : days = days + ",fr"
    else : days = days + "fr"
  if meetDate["saturday"] =="S":
    if len(days) > 0 : days = days + ",sa"
    else : days = days + "sa"

  if ( (len(startTime) == 0) or (len(origDays) == 0)) :
    entry = "  NO Event Created.  No startTime and No Days of Week.  sched.id = %s\n" % (meetId)
    return (entry, eventId)

  startTime = startTime[0:2] + ":" + startTime[2:4]
  endTime = endTime[0:2] + ":" + endTime[2:4]

  if (startDate < dstLastYear["start"].date()):
    offSet = ":00.000-09:00"
  elif (startDate > dstLastYear["start"].date() and startDate < dstLastYear["end"].date()):
    offSet = ":00.000-08:00"
  elif (startDate > dstLastYear["end"].date() and startDate < dstThisYear["start"].date()):
    offSet = ":00.000-09:00"
  elif(startDate > dstThisYear["start"].date() and startDate < dstThisYear["end"].date()):
    offSet = ":00.000-08:00"
  elif(startDate > dstThisYear["end"].date() and startDate < dstNextYear["start"].date()):
    offSet = ":00.000-09:00"
  elif(startDate > dstNextYear["start"].date() and startDate < dstNextYear["end"].date()):
    offSet = ":00.000-08:00"
  elif(startDate > dstNextYear["end"].date()):
    offSet = ":00.000-09:00"
  else:
    print "ERROR: something is wrong with new dst code\n"

  print "  offset = %s" % offSet
  start = startDate.strftime("%Y-%m-%d") + "T" + startTime + offSet 
  end =  startDate.strftime("%Y-%m-%d") + "T" + endTime + offSet 

  until = meetDate["meetEndDate"].strftime("%Y-%m-%d") + " 23:59:59"
  until = time.strftime("%Y%m%dT%H%M%SZ",
          time.gmtime(time.mktime(time.strptime(until,
                                  "%Y-%m-%d %H:%M:%S"))))
  recurrUntil = 'RRULE:FREQ=WEEKLY;BYDAY=' + str(days) +';UNTIL=' + until + '\r\n'

  event = {
            'description': crn,
            'summary': course,
            'location': where,
            'start': {
                       'dateTime': start,
                       'timeZone': 'America/Anchorage' 
                     },
            'end': {
                     'dateTime': end,
                     'timeZone': 'America/Anchorage' 
                   },
            'recurrence' : [recurrUntil,]
          }

  quota = 0
  for i in range(0,10):
    try:
      new_event = service.events().insert(calendarId=calId, body=event).execute()
    except HttpError, errorCode:
      errorReason = errorCode.resp.reason
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      if ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"
          return (entry, eventId)
      elif ("Forbidden" in errorCode):
        entry = "  FAILED: FORBIDDEN"
        return (entry, eventId)
      continue
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      print "** Create calendar NOT http error informaton => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      if ("invalid" in errorCode):
        entry = "  FAILED: INVALID CREDENTIALS"
        return (entry, eventId)
      entry = "%s | %s" % (entry, error)
      continue
    break

  try:
    eventId = new_event['id']
  except NameError:
    entry = "** ERROR: EVENTS NOT CREATED meetId - %s, crn and term = %s, %s\n" % (meetDate["id"], crn, term)
    return (entry, eventId)

  print "  calid = %s" % calId

  entry = "  recurrence event added successfully = %s, eventId = %s\n" % (event, new_event['id'])

  return (entry, eventId) 

###############################
# Delete a secondary calendar #
###############################
def delete_cal(calId, service, setTrace=False):
  entry = "  Successfully deleted calId = %s" % calId
  quota = 0

  if setTrace:
    pdb.set_trace()

  for i in range(0,10):
    try:
      service.calendarList().delete(calendarId=calId).execute()
    except HttpError, errorCode:
      errorReason = errorCode.resp.reason 
      entry = "UNEXISTANCE: Did not find calId = %s\n" % calId 
      if ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"
          return entry
      elif ("Forbidden" in errorCode):
        entry = "  FAILED: FORBIDDEN"
        return entry
      elif ("Not Found" in errorReason):
        if (i >= 2):
          return entry
      continue
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      print "** Create calendar NOT http error informaton => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      if ("invalid" in errorCode):
        entry = "  FAILED: INVALID CREDENTIALS"
        return entry
      entry = "%s | %s" % (entry, error)
      continue
    break

  return entry

#################################
# return beginning / end of DST #
#################################
def first_sunday_on_or_after(dt, setTrace=False):
  from datetime import timedelta

  if setTrace:
    pdb.set_trace()

  days_to_go = 6 - dt.weekday()
  if days_to_go:
    dt += timedelta(days_to_go)
  return dt

######################
# error code cleanup #
######################
def error_code_cleanup(fullError, setTrace=False):
  if setTrace:
    pdb.set_trace()

  errorStr = "%s" % (fullError)

  quote = errorStr.find('\"') + 1
  error = errorStr[quote:]
  quote = error.find('\"')
  error = error[:quote]
  print "=> error code cleanup, error = %s" % error
  return error

########################################
# return subject from subjCourseNumSeq #
########################################
def return_subject(subjCourseNumSeq, setTrace=False):
  if setTrace:
    pdb.set_trace()

  (subject, dc, sdc) = subjCourseNumSeq.split(' ')
  return subject

#####################################
# return service from account build #
#####################################
def return_service(requestor, credentials, setTrace=False):
  entry = ""
  quota = 0

  if setTrace:
    pdb.set_trace()

  http = httplib2.Http()
  http = credentials.authorize(http)
  for i in range(0,10):
    try:
      service = build(serviceName='calendar', version='v3', http=http)
    except HttpError, errorCode:
      errorReason = errorCode.resp.reason
      if ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"
      else:
        entry = "ERROR: %s" % errorCode
      continue
    break

    try:
      service
    except NameError:
      service = "FAILED"
 
  return (entry, service)    

##########################################
# return a list of calIds for an account #
##########################################
def return_calendars(service, setTrace=False):
  entry = ""
  calList = {}

  if setTrace:
    pdb.set_trace()

  for i in range(0,5):
    if setTrace:
      pdb.set_trace()

    try:
      calendar_list = service.calendarList().list().execute()
    except HttpError, errorCode:
      errorReason = errorCode.resp.reason
      entry = "UNEXISTANCE: Did not find calId = %s\n" % calId
      if ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"
          return entry
      elif ("Forbidden" in errorCode):
        entry = "  FAILED: FORBIDDEN"
        return entry
      elif ("Not Found" in errorReason):
        if (i >= 2):
          return entry
      continue
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      print "** Create calendar NOT http error information => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      if ("invalid" in errorCode):
        entry = "  FAILED: INVALID CREDENTIALS"
        return entry
      entry = "%s | %s" % (entry, error)
      continue
    break

  calendarCount = 0

  while True:
    for calEntry in calendar_list['items']:
      if setTrace:
        pdb.set_trace()

      calendarCount += 1
      calId = calEntry['id']

      if ('description' in calEntry):
        description = calEntry['description']
        crn = description[4:9]
      else: 
        crn = ""

      if ('summary' in calEntry):      
        title = calEntry['summary']
        term = title[-6:]
      else: title = ""

      calList[calId] = { 'crn':crn, 'term':term }     
       
    page_token = calendar_list.get('nextPageToken')
    if page_token:
      calendar_list = service.calendarList().list(pageToken=page_token).execute()
    else:
      break

  return calList

##################################
# returns list of holiday events #
##################################
def return_holidays(holidayCalId, service, term=0, setTrace=False):
  if setTrace:
    pdb.set_trace()

  holidayListing = []
  start = ""
  end = ""
  entry = ""
  
  if (term > 0):
    # term in format 201401, 201402 or 201403
    # as general timeframe 01 is Jan 01 to Jun 01, term 02 is May 01 to Sept 01 and term 03 is Aug 01 to Jan 01
    # timeMin & Max format should be YYYY-MM-DDT00:00:00-0800
    year = str(term)[0:4]
    semester = str(term)[4:7]

    if (semester == '01'): 
      start = '%s-01-01T00:00:00-0800' % (year)
      end = '%s-06-01T00:00:00-0800' % (year)
    elif (semester == '02'):
      start = '%s-05-01T00:00:00-0800' % (year)
      end = '%s-09-01T00:00:00-0800' % (year)
    elif (semester == '03'):
      start = '%s-08-01T00:00:00-0800' % (year)
      end = '%s-01-01T00:00:00-0800' % (year)

  for i in range(0,5):
    if setTrace:
      pdb.set_trace()

    try:
      if (term > 0):
        holidayEvents = service.events().list(calendarId=holidayCalId, orderBy='startTime', singleEvents=True, timeMin=start, timeMax=end).execute()
      else:
        holidayEvents = service.events().list(calendarId=holidayCalId, orderBy='startTime', singleEvents=True).execute()
    except HttpError, errorCode:
      errorReason = errorCode.resp.reason
      entry = "UNEXISTANCE: Did not find calId = %s\n" % holidayCalId 
      if ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"
          return (entry, holidayListing)
      elif ("Forbidden" in errorCode):
        entry = "  FAILED: FORBIDDEN"
        return (entry, holidayListing)
      elif ("Not Found" in errorReason):
        if (i >= 2):
          return (entry, holidayListing)
      continue
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      print "** Create calendar NOT http error information => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      if ("invalid" in errorCode):
        entry = "  FAILED: INVALID CREDENTIALS"
        return (entry, holidayListing)
      entry = "%s | %s" % (entry, error)
      continue
    break

  for holidays in holidayEvents['items']:
    try:
      holidayListing.append(holidays['start']['date'])
    except:
      print "** Creating Holiday Listing: error found when attempting to append the returned holidays to holidayListing"
      continue

  return (entry, holidayListing)

#############################################################
# cancels or deletes events scheduled during class holidays #
#############################################################
def cancel_holiday_classes(holidays, calId, eventID, service, setTrace=False):
  entry = "  SUCCESS no classes to remove"

  if setTrace:
    pdb.set_trace()

  for i in range(0,5):
    if setTrace:
      pdb.set_trace()
  
    try:
      instances = service.events().instances(calendarId=calId, eventId=eventID).execute()
    except HttpError, errorCode:
      errorReason = errorCode.resp.reason
      entry = "UNEXISTANCE: Did not find calId = %s\n" % calId 
      if ("Quota" in errorCode or "Exceeded" in errorCode or "limits exceeded" in errorCode):
        if (quota <= 5):
          quota += 1
        else:
          entry = "  FAILED: LIMIT REACHED"
          return entry
      elif ("Forbidden" in errorCode):
        entry = "  FAILED: FORBIDDEN"
        return entry
      elif ("Not Found" in errorReason):
        if (i >= 2):
          return entry
      continue
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      print "** Create calendar NOT http error information => type = %r, error = %r,  errorCode = %r\n" % (exctype, error, errorCode)
      if ("invalid" in errorCode):
        entry = "  FAILED: INVALID CREDENTIALS"
        return entry
      entry = "%s | %s" % (entry, error)
      continue
    break

  if ('items' in instances):
    for event in instances['items']:
      if setTrace: pdb.set_trace()
      fullDateTime = event['start']['dateTime']
      eventDate = fullDateTime[0:10]
      if (eventDate in holidays):
        # Select the instance to cancel.
        cancelMe = event
        cancelMe['status'] = 'cancelled'
        try:
          updatedInstance = service.events().update(calendarId=calId, eventId=cancelMe['id'], body=cancelMe).execute()
        except:
          exctype, error = sys.exc_info()[:2]
          errorCode = error_code_cleanup(error)
          if setTrace: pdb.set_trace()
          return errorCode

        # Print the updated date.
        try:
          updatedInstance['updated']  
        except:
          exctype, error = sys.exc_info()[:2]
          errorCode = error_code_cleanup(error)
          return errorCode
        entry = "  SUCCESS canceled holiday event"
  else: 
    try:
      event = service.events().get(calendarId=calId, eventId=eventID).execute()
    except:
      exctype, error = sys.exc_info()[:2]
      errorCode = error_code_cleanup(error)
      return errorCode

    eventDate = event['start']['date']
    if (eventDate in holidays):
      try:
        service.events().delete(calendarId=calId, eventId=eventId).execute()
      except:
        exctype, error = sys.exc_info()[:2]
        errorCode = error_code_cleanup(error)
        return errorCode
    entry = "  SUCCESS deleted holiday event"

  if setTrace:  pdb.set_trace()

  return entry
 
 

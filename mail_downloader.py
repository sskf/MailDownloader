from bs4 import BeautifulSoup
import copy
import datetime
import email
from email import header,utils
import getopt
import imaplib
import json
import logging
import os
import platform
import pytz
import re
import requests
import rtoml
import socket
import sys
import time
import threading
import traceback
import urllib.parse

_version = '1.4.0-Alpha'
_mode = 1  # 0:Release;1:Alpha;2:Beta;3:Demo
_regex_flag_dict={
    'a':re.ASCII,
    'i':re.IGNORECASE,
    'l':re.LOCALE,
    'm':re.MULTILINE,
    's':re.DOTALL,
    'x':re.VERBOSE,
    'u':re.UNICODE
}

config_custom_path_global=None
is_config_path_relative_to_program_global=False

authentication = ['name', 'MailDownloader', 'version', _version]
available_largefile_website_list_global = [
    'wx.mail.qq.com', 'mail.qq.com', 'dashi.163.com', 'mail.163.com', 'mail.sina.com.cn']  # 先后顺序不要动!
unavailable_largefile_website_list_global = []
website_blacklist = ['fs.163.com', 'u.163.com']

thread_excepion_list_global=[]

lock_print_global = threading.Lock()
lock_var_global = threading.Lock()
lock_io_global = threading.Lock()

log_global=logging.getLogger('logger')
log_global.setLevel(logging.DEBUG)
log_debug_handler_global=logging.StreamHandler()
log_debug_handler_global.setLevel(logging.DEBUG)
log_global.addHandler(log_debug_handler_global)
class Date():
    __month_dict = {1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May',
                    6: 'Jun', 7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'}
    year = 1
    month = 1
    day = 1
    enabled = False

    def __init__(self, enabled=False, year=0, month=0, day=0):
        self.enabled = enabled
        if year > 0:
            self.year = year
        if month > 0:
            self.month = month
        if day > 0:
            self.day = day

    def time(self):
        return '{:0>2d}-{}-{:0>4d}'.format(self.day, self.__month_dict[self.month], self.year)


config_load_state = False
config_primary_data = {
    'mail': [],
    'allow_manual_input_search_date': True,
    'min_search_date': False,
    'max_search_date': False,
    'only_search_unseen_mails': True,
    'thread_count': 4,
    'rollback_when_download_failed': True,
    'sign_unseen_tag_after_downloading': True,
    'reconnect_max_times': 3,
    'download_path': ''
}
def operation_load_config_new():
    global host_global,address_global,password_global
    global setting_silent_download_mode_global
    global setting_enable_log_global,log_file_handler_global
    global setting_search_mailbox_global
    global setting_search_mails_type_global
    global setting_manual_input_search_date_global
    global setting_min_search_date_global,setting_max_search_date_global
    global setting_filter_sender_global,setting_filter_sender_mode_global,setting_filter_subject_global,setting_filter_subject_mode_global
    global setting_download_thread_count_global
    global setting_rollback_when_download_failed_global
    global setting_sign_unseen_tag_after_downloading_global
    global setting_reconnect_max_times_global
    global setting_deafult_download_path_global, setting_mime_type_classfication_path_global,setting_file_name_classfication_path_global

    print('正在读取配置文件...(NEW)', flush=True)
    try:
        if config_custom_path_global:
            if is_config_path_relative_to_program_global:
                config_path=os.path.join(get_path(), config_custom_path_global)
            else:
                config_path=config_custom_path_global
        else:
            config_path=os.path.join(get_path(), 'test','config_1_4.toml')
        with open(config_path, 'rb') as config_file:
            config_file_data = rtoml.load(
                bytes.decode(config_file.read(), 'utf-8'))

            setting_silent_download_mode_global=config_file_data['program']['silent_download_mode']
            assert isinstance(setting_silent_download_mode_global,bool)
            
            log=config_file_data['program']['log']
            if log!=False:
                assert isinstance(log,dict) and isinstance(log['path'],str) and isinstance(log['relative_to_program'],bool) and isinstance(log['overwrite'],bool)
                setting_enable_log_global=True
                log_write_type='w' if log['overwrite'] else 'a'
                log_path=os.path.join(get_path(), log['path']) if log['relative_to_program'] else log['path']
                log_name = datetime.datetime.strftime(datetime.datetime.now(),'%Y-%m-%d')+'.log'
                try:
                    if not os.path.exists(log_path):
                        os.makedirs(log_path)
                    for handler in log_global.handlers:
                         if type(handler)==logging.FileHandler:
                            handler.close()
                            log_global.removeHandler(handler)
                    log_file_handler_global=logging.FileHandler(os.path.join(log_path,log_name),log_write_type,'utf-8')
                    log_file_handler_global.setLevel(logging.INFO)
                    log_global.addHandler(log_file_handler_global)
                except OSError as e:
                    print('E: 日志文件创建错误.',flush=True)
                    raise e
            else:
                setting_enable_log_global=False

            host_global=[]
            address_global=[]
            password_global=[]
            user_data=config_file_data['mail']['user_data']
            assert isinstance(user_data,list)
            for user_data_splited in user_data:
                assert isinstance(user_data_splited,dict) and isinstance(user_data_splited['host'],str) and isinstance(user_data_splited['address'],str) and isinstance(user_data_splited['password'],str)
                host_global.append(user_data_splited['host'])
                address_global.append(user_data_splited['address'])
                password_global.append(user_data_splited['password'])
            
            mailbox=config_file_data['search']['mailbox']
            assert isinstance(mailbox,list)
            for j in mailbox:
                assert isinstance(j,list)
            search_mailbox=operation_parse_config_data1(mailbox,True,'inbox')[1]
            setting_search_mailbox_global=search_mailbox

            setting_search_mails_type_global=config_file_data['search']['search_mail_type']
            assert isinstance(setting_search_mails_type_global,int) and 0<=setting_search_mails_type_global<=2
            
            setting_manual_input_search_date_global=config_file_data['search']['date']['manual_input_search_date']
            assert isinstance(setting_manual_input_search_date_global,bool)

            setting_min_search_date_global=Date()
            min_search_date=config_file_data['search']['date']['min_search_date']
            assert isinstance(min_search_date,list)
            if len(min_search_date)>0:
                assert isinstance(min_search_date[0],int) and min_search_date[0]>=1
                setting_min_search_date_global.enabled=True
                setting_min_search_date_global.year=min_search_date[0]
            if len(min_search_date)>1:
                assert isinstance(min_search_date[1],int) and 1<=min_search_date[1]<=12
                setting_min_search_date_global.enabled=True
                setting_min_search_date_global.year=min_search_date[1]
            if len(min_search_date)>2:
                assert isinstance(min_search_date[2],int) and 1<=min_search_date[2]<=31
                setting_min_search_date_global.enabled=True
                setting_min_search_date_global.year=min_search_date[2]

            setting_max_search_date_global=Date()
            max_search_date=config_file_data['search']['date']['max_search_date']
            assert isinstance(max_search_date,list)
            if len(max_search_date)>0:
                assert isinstance(max_search_date[0],int) and max_search_date[0]>=1
                setting_max_search_date_global.enabled=True
                setting_max_search_date_global.year=max_search_date[0]
            if len(max_search_date)>1:
                assert isinstance(max_search_date[1],int) and 1<=max_search_date[1]<=12
                setting_max_search_date_global.enabled=True
                setting_max_search_date_global.year=max_search_date[1]
            if len(max_search_date)>2:
                assert isinstance(max_search_date[2],int) and 1<=max_search_date[2]<=31
                setting_max_search_date_global.enabled=True
                setting_max_search_date_global.year=max_search_date[2]
            
            filter_sender=[]
            filter_sender_mode=[]
            sender_name_raw=config_file_data['search']['filter']['sender_name']
            assert isinstance(sender_name_raw,dict)
            sender_name_expression=sender_name_raw['exp']
            assert isinstance(sender_name_expression,list)
            sender_name_mode=sender_name_raw['mode']
            assert isinstance(sender_name_mode,list)
            filter_sender_name=operation_parse_config_data1(sender_name_expression)[1]
            filter_sender_name_mode=operation_parse_config_data1(sender_name_mode,False,'')
            filter_sender_name_mode=operation_parse_regex_mode(filter_sender_name_mode[1],filter_sender_name,filter_sender_name_mode[0])
            assert operation_validate_regex(filter_sender_name,filter_sender_name_mode)
            filter_sender.append(filter_sender_name)
            filter_sender_mode.append(filter_sender_name_mode)
            sender_address_raw=config_file_data['search']['filter']['sender_address']
            assert isinstance(sender_address_raw,dict)
            sender_address_expression=sender_address_raw['exp']
            assert isinstance(sender_address_expression,list)
            sender_address_mode=sender_address_raw['mode']
            assert isinstance(sender_address_mode,list)
            filter_sender_address=operation_parse_config_data1(sender_address_expression)[1]
            filter_sender_address_mode=operation_parse_config_data1(sender_address_mode,False,'')
            filter_sender_address_mode=operation_parse_regex_mode(filter_sender_address_mode[1],filter_sender_address,filter_sender_address_mode[0])
            assert operation_validate_regex(filter_sender_address,filter_sender_address_mode)
            filter_sender.append(filter_sender_address)
            filter_sender_mode.append(filter_sender_address_mode)
            setting_filter_sender_global=filter_sender
            setting_filter_sender_mode_global=filter_sender_mode

            subject_raw=config_file_data['search']['filter']['subject']
            assert isinstance(subject_raw,dict)
            subject_expression=subject_raw['exp']
            assert isinstance(subject_expression,list)
            subject_mode=subject_raw['mode']
            assert isinstance(subject_mode,list)
            filter_subject=operation_parse_config_data1(subject_expression)[1]
            filter_subject_mode=operation_parse_config_data1(subject_mode,False,'')
            filter_subject_mode=operation_parse_regex_mode(filter_subject_mode[1],filter_subject,filter_subject_mode[0])
            assert operation_validate_regex(filter_subject,filter_subject_mode)
            setting_filter_subject_global=filter_subject
            setting_filter_subject_mode_global=filter_subject_mode
            
            setting_download_thread_count_global=config_file_data['download']['thread_count']
            assert isinstance(setting_download_thread_count_global,int) and setting_download_thread_count_global>0
            
            setting_rollback_when_download_failed_global=config_file_data['download']['rollback_when_download_failed']
            assert isinstance(setting_rollback_when_download_failed_global,bool)

            setting_sign_unseen_tag_after_downloading_global=config_file_data['download']['sign_unseen_tag_after_downloading']
            assert isinstance(setting_sign_unseen_tag_after_downloading_global,bool)

            setting_reconnect_max_times_global=config_file_data['download']['reconnect_max_times']
            assert isinstance(setting_reconnect_max_times_global,int)

            default_download_path_raw=config_file_data['download']['path']['default']
            assert isinstance(default_download_path_raw,dict) and isinstance(default_download_path_raw['path'],str) and isinstance(default_download_path_raw['relative_to_program'],bool)
            default_download_path=os.path.join(get_path(), default_download_path_raw['path']) if default_download_path_raw['relative_to_program'] else default_download_path_raw['path']
            try:
                if not os.path.exists(default_download_path):
                    os.makedirs(default_download_path)
            except OSError as e:
                print('E: 路径创建错误.',flush=True)
                raise e
            setting_deafult_download_path_global=default_download_path

            mime_type_classfication=[]
            mime_type_classfication_raw=config_file_data['download']['path']['mime_type_classfication']
            assert isinstance(mime_type_classfication_raw,list)
            for mime_type_classfication_splited in mime_type_classfication_raw:
                assert isinstance(mime_type_classfication_splited,dict) and isinstance(mime_type_classfication_splited['type'],dict) and isinstance(mime_type_classfication_splited['path'],str) and isinstance(mime_type_classfication_splited['relative_to_download_path'],bool)
                mime_type_classfication.append([])
                mime_type_classfication_splited_expression=mime_type_classfication_splited['type']['exp']
                assert isinstance(mime_type_classfication_splited_expression,list)
                for j in mime_type_classfication_splited_expression:
                    assert isinstance(j,str)
                mime_type_classfication_splited_expression=operation_parse_config_data1(mime_type_classfication_splited_expression)[1]
                mime_type_classfication_splited_mode=mime_type_classfication_splited['type']['mode']
                for j in mime_type_classfication_splited_mode:
                    assert isinstance(j,str)
                mime_type_classfication_splited_mode=operation_parse_config_data1(mime_type_classfication_splited_mode,False,'')
                mime_type_classfication_splited_mode=operation_parse_regex_mode(mime_type_classfication_splited_mode[1],mime_type_classfication_splited_expression)
                assert operation_validate_regex(mime_type_classfication_splited_expression,mime_type_classfication_splited_mode)
                mime_type_classfication_splited_expression=mime_type_classfication_splited_expression[0]
                mime_type_classfication_splited_mode=mime_type_classfication_splited_mode[0]
                mime_type_classfication_splited_download_path=os.path.join(default_download_path, mime_type_classfication_splited['path']) if mime_type_classfication_splited['relative_to_download_path'] else mime_type_classfication_splited['path']
                try:
                    if not os.path.exists(mime_type_classfication_splited_download_path):
                        os.makedirs(mime_type_classfication_splited_download_path)
                except OSError as e:
                    print('E: 路径创建错误.',flush=True)
                    raise e
                mime_type_classfication[-1].append(mime_type_classfication_splited_expression)
                mime_type_classfication[-1].append(mime_type_classfication_splited_mode)
                mime_type_classfication[-1].append(mime_type_classfication_splited_download_path)
            setting_mime_type_classfication_path_global=mime_type_classfication
            
            file_name_classfication=[]
            file_name_classfication_raw=config_file_data['download']['path']['file_name_classfication']
            assert isinstance(file_name_classfication_raw,list)
            for file_name_classfication_splited in file_name_classfication_raw:
                assert isinstance(file_name_classfication_splited,dict) and isinstance(file_name_classfication_splited['type'],dict) and isinstance(file_name_classfication_splited['path'],str) and isinstance(file_name_classfication_splited['extension'],bool) and isinstance(file_name_classfication_splited['relative_to_download_path'],bool)
                file_name_classfication.append([])
                file_name_classfication_splited_expression=file_name_classfication_splited['type']['exp']
                assert isinstance(file_name_classfication_splited_expression,list)
                for j in file_name_classfication_splited_expression:
                    assert isinstance(j,str)
                file_name_classfication_splited_expression=operation_parse_config_data1(file_name_classfication_splited_expression)[1]
                file_name_classfication_splited_mode=file_name_classfication_splited['type']['mode']
                for j in file_name_classfication_splited_mode:
                    assert isinstance(j,str)
                file_name_classfication_splited_mode=operation_parse_config_data1(file_name_classfication_splited_mode,False,'')
                file_name_classfication_splited_mode=operation_parse_regex_mode(file_name_classfication_splited_mode[1],file_name_classfication_splited_expression)
                assert operation_validate_regex(file_name_classfication_splited_expression,file_name_classfication_splited_mode)
                file_name_classfication_splited_expression=file_name_classfication_splited_expression[0]
                file_name_classfication_splited_mode=file_name_classfication_splited_mode[0]
                file_name_classfication_splited_download_path=os.path.join(default_download_path, file_name_classfication_splited['path']) if file_name_classfication_splited['relative_to_download_path'] else file_name_classfication_splited['path']
                try:
                    if not os.path.exists(file_name_classfication_splited_download_path):
                        os.makedirs(file_name_classfication_splited_download_path)
                except OSError as e:
                    print('E: 路径创建错误.',flush=True)
                    raise e
                file_name_classfication[-1].append(file_name_classfication_splited_expression)
                file_name_classfication[-1].append(file_name_classfication_splited_mode)
                file_name_classfication[-1].append(file_name_classfication_splited['extension'])
                file_name_classfication[-1].append(file_name_classfication_splited_download_path)
            setting_file_name_classfication_path_global=file_name_classfication

            # log_global.debug(setting_reconnect_max_times_global)
            # log_global.debug(setting_search_mailbox_global)
            # log_global.debug(setting_filter_sender_global)
            # log_global.debug(setting_filter_sender_mode_global)
            # log_global.debug(setting_filter_subject_global)
            # log_global.debug(setting_filter_subject_mode_global)
            # log_global.debug(setting_mime_type_classfication_path_global)
            # log_global.debug(setting_file_name_classfication_path_global)
    except Exception as e:
        if str(e):
            print('E: 配置文件错误,信息如下:', flush=True)
            print(repr(e),flush=True)
        else:
            print('E: 配置文件错误.', flush=True)
        return False
    else:
        print('配置加载成功.', flush=True)
        return True
def operation_parse_config_data1(source,ignore_empty_str=True,*default):
    target=[[],[]]
    processed_count=0
    for i in range(len(source)):
        if isinstance(source[i],list):
            if processed_count==len(host_global):
                continue
            target[1].append([])
            for j in source[i]:
                assert isinstance(j,str)
                if j or not ignore_empty_str:
                    target[1][-1].append(j)
            if not len(target[1][-1]):
                target[1][-1]=target[0]
            processed_count+=1
        elif isinstance(source[i],str):
            if source[i]:
                target[0].append(source[i])
        else:
            raise ValueError
    for i in range(len(host_global)-processed_count):
        target[1].append(target[0])
            
    if not len(target[0]) and len(default):
        for j in default:
            target[0].append(j)
    return target
def operation_parse_regex_mode(source,compare,deafult=['']):#将正则表达式模式项与表达式项对齐并转成数字形式
    target=[]
    source_default_tmp=''
    for j in deafult:
        source_default_tmp+=j
    deafult[0]=source_default_tmp
    for i in range(len(compare)):
        target.append([])
        for i2 in range(min(len(source[i]),len(compare[i]))):
            target[-1].append(source[i][i2])
        for i2 in range(len(compare[i])-len(source[i])):
            target[-1].append(deafult[0])
    for i in range(len(target)):
        for i2 in range(len(target[i])):
            regex_flag=0
            for j in target[i][i2]:
                regex_flag|=int(_regex_flag_dict[j])
            target[i][i2]=regex_flag
    return target
def operation_validate_regex(expression,mode):#验证正则表达式是否正确
    for i in range(len(expression)):
        for i2 in range(len(expression[i])):
            try:
                # log_global.debug(expression[i][i2])
                # log_global.debug(mode[i][i2])
                re.compile(expression[i][i2],mode[i][i2])
            except re.error:
                return False
    return True
def operation_load_config():
    global host, address, password
    global setting_allow_manual_input_search_date, setting_mail_min_date, setting_mail_max_date
    global setting_only_search_unseen_mails
    global setting_thread_count
    global setting_rollback_when_download_failed
    global setting_sign_unseen_tag_after_downloading
    global setting_reconnect_max_times
    global setting_download_path
    print('正在读取配置文件...', flush=True)
    try:
        if config_custom_path_global:
            if is_config_path_relative_to_program_global:
                config_path=os.path.join(get_path(), config_custom_path_global)
            else:
                config_path=config_custom_path_global
        else:
            config_path=os.path.join(get_path(), 'config.toml')
        with open(config_path, 'rb') as config_file:
            config_file_data = rtoml.load(
                bytes.decode(config_file.read(), 'utf-8'))
            host = []
            address = []
            password = []
            for eachdata_mail in config_file_data['mail']:
                if type(eachdata_mail['host']) != str:
                    raise ValueError
                host.append(eachdata_mail['host'])
                if type(eachdata_mail['address']) != str:
                    raise ValueError
                address.append(eachdata_mail['address'])
                if type(eachdata_mail['password']) != str:
                    raise ValueError
                password.append(eachdata_mail['password'])
            setting_allow_manual_input_search_date = config_file_data[
                'allow_manual_input_search_date']
            if type(setting_allow_manual_input_search_date) != bool:
                raise ValueError
            setting_mail_min_date = Date()
            if config_file_data['min_search_date'] == False:
                setting_mail_min_date.enabled = False
            else:
                setting_mail_min_date.enabled = True
                setting_mail_min_date.year = config_file_data['min_search_date'][0]
                if type(setting_mail_min_date.year) != int:
                    raise ValueError
                setting_mail_min_date.month = config_file_data['min_search_date'][1]
                if type(setting_mail_min_date.month) != int:
                    raise ValueError
                setting_mail_min_date.day = config_file_data['min_search_date'][2]
                if type(setting_mail_min_date.day) != int:
                    raise ValueError
            setting_mail_max_date = Date()
            if config_file_data['max_search_date'] == False:
                setting_mail_max_date.enabled = False
            else:
                setting_mail_max_date.enabled = True
                setting_mail_max_date.year = config_file_data['max_search_date'][0]
                if type(setting_mail_max_date.year) != int:
                    raise ValueError
                setting_mail_max_date.month = config_file_data['max_search_date'][1]
                if type(setting_mail_max_date.month) != int:
                    raise ValueError
                setting_mail_max_date.day = config_file_data['max_search_date'][2]
                if type(setting_mail_max_date.day) != int:
                    raise ValueError
            setting_only_search_unseen_mails = config_file_data['only_search_unseen_mails']
            if type(setting_only_search_unseen_mails) != bool:
                raise ValueError
            setting_thread_count = config_file_data['thread_count']
            if type(setting_thread_count) != int or setting_thread_count < 1:
                raise ValueError
            setting_rollback_when_download_failed = config_file_data[
                'rollback_when_download_failed']
            if type(setting_rollback_when_download_failed) != bool:
                raise ValueError
            setting_sign_unseen_tag_after_downloading = config_file_data[
                'sign_unseen_tag_after_downloading']
            if type(setting_allow_manual_input_search_date) != bool:
                raise ValueError
            setting_reconnect_max_times = config_file_data['reconnect_max_times']
            if type(setting_reconnect_max_times) != int and setting_reconnect_max_times < 0:
                raise ValueError
            setting_download_path = config_file_data['download_path']
    except (OSError,FileNotFoundError):
        print('E: 配置文件不存在.', flush=True)
        return False
    except:
        print('E: 配置文件错误.', flush=True)
        return False
    else:
        print('配置加载成功.', flush=True)
        return True


def init():
    global stop_state_global
    global has_thread_state_changed_global
    global imap_list_global, imap_succeed_index_int_list_global, imap_connect_failed_index_int_list_global, imap_with_undownloadable_attachments_index_int_list_global, imap_overdueanddeleted_index_int_list_global, imap_fetch_failed_index_int_list_global, imap_download_failed_index_int_list_global
    global msg_processed_count_global, msg_list_global, msg_with_undownloadable_attachments_list_global, msg_with_downloadable_attachments_list_global, msg_overdueanddeleted_list_global, msg_fetch_failed_list_global, msg_download_failed_list_global
    global send_time_with_undownloadable_attachments_list_global, send_time_overdueanddeleted_list_global, send_time_download_failed_list_global
    global subject_with_undownloadable_attachments_list_global, subject_overdueanddeleted_list_global, subject_download_failed_list_global
    global file_download_count_global, file_name_raw_list_global, file_name_list_global
    global largefile_undownloadable_link_list_global
    global largefile_undownloadable_code_list_global
    stop_state_global = 0
    has_thread_state_changed_global = True

    imaplib.Commands['ID'] = ('AUTH')
    imap_list_global = []
    imap_succeed_index_int_list_global = []
    imap_connect_failed_index_int_list_global = []
    imap_with_undownloadable_attachments_index_int_list_global = []
    imap_overdueanddeleted_index_int_list_global = []
    imap_fetch_failed_index_int_list_global = []
    imap_download_failed_index_int_list_global = []

    msg_processed_count_global = 0
    msg_list_global = []
    msg_with_undownloadable_attachments_list_global = []
    msg_with_downloadable_attachments_list_global = []
    msg_overdueanddeleted_list_global = []
    msg_fetch_failed_list_global = []
    msg_download_failed_list_global = []
    send_time_with_undownloadable_attachments_list_global = []
    send_time_overdueanddeleted_list_global = []
    send_time_download_failed_list_global = []
    subject_with_undownloadable_attachments_list_global = []
    subject_overdueanddeleted_list_global = []
    subject_download_failed_list_global = []
    file_download_count_global = 0
    file_name_raw_list_global = []
    file_name_list_global = []
    largefile_undownloadable_link_list_global = []  # 2级下载链接
    largefile_undownloadable_code_list_global = []
    for i in range(len(host)):
        msg_list_global.append([])
        msg_with_undownloadable_attachments_list_global.append([])
        msg_with_downloadable_attachments_list_global.append([])
        msg_overdueanddeleted_list_global.append([])
        msg_fetch_failed_list_global.append([])
        msg_download_failed_list_global.append([])
        send_time_with_undownloadable_attachments_list_global.append([])
        send_time_overdueanddeleted_list_global.append([])
        send_time_download_failed_list_global.append([])
        subject_with_undownloadable_attachments_list_global.append([])
        subject_overdueanddeleted_list_global.append([])
        subject_download_failed_list_global.append([])
        file_name_raw_list_global.append([])
        file_name_list_global.append([])
        largefile_undownloadable_link_list_global.append([])
        largefile_undownloadable_code_list_global.append([])


def operation_login_imap_server(host, address, password, display=True):
    is_login_succeed = False
    try:
        if display:
            print('\r正在连接 ', host,
                  indent(3), end='', sep='', flush=True)
        imap = imaplib.IMAP4_SSL(
            host)
        if display:
            print('\r已连接 ', host,
                  indent(3), sep='', end='', flush=True)
            print('\r正在登录 ', address, indent(3),
                  end='', sep='', flush=True)
        imap.login(address, password)
        if display:
            print('\r', address,
                  ' 登录成功', indent(3), sep='', flush=True)
        imap._simple_command(
            'ID', '("' + '" "'.join(authentication) + '")')  # 发送ID
    except imaplib.IMAP4.error:
        if display:
            print('\nE: 用户名或密码错误.', flush=True)
    except (socket.timeout, TimeoutError):
        if display:
            print('\nE: 服务器连接超时.', flush=True)
    except Exception:
        if display:
            print('\nE: 服务器连接错误.', flush=True)
    else:
        is_login_succeed = True
    if is_login_succeed:
        imap.select()
        return imap
    else:
        return None


def operation_login_all_imapserver():
    init()
    for imap_index_int in range(len(host)):
        imap = operation_login_imap_server(
            host[imap_index_int], address[imap_index_int], password[imap_index_int])
        imap_list_global.append(imap)
        if imap != None:
            imap_succeed_index_int_list_global.append(imap_index_int)
        else:
            imap_connect_failed_index_int_list_global.append(imap_index_int)
    if len(host):
        if len(imap_succeed_index_int_list_global):
            print('已成功连接的邮箱:', flush=True)
            for imap_succeed_index_int in imap_succeed_index_int_list_global:
                print(indent(1), address[imap_succeed_index_int], sep='')
            if len(imap_succeed_index_int_list_global) < len(host):
                print('E: 以下邮箱未能连接:', flush=True)
                for imap_connect_failed_index_int in imap_connect_failed_index_int_list_global:
                    print(indent(1), address[imap_connect_failed_index_int],
                          sep='', flush=True)
        else:
            print('E: 没有成功连接的邮箱.', flush=True)
    else:
        print('E: 没有邮箱.')


def operation_set_time():
    setting_mail_min_date.enabled = False
    setting_mail_max_date.enabled = False
    if input_option('是否设置检索开始日期?', 'y', 'n', default_option='y', end=':') == 'y':
        setting_mail_min_date.enabled = True
        while True:
            try:
                setting_mail_min_date.year = int(input_option(
                    '输入年份', allow_undefind_input=True, default_option=str(datetime.datetime.now().year), end=':'))
                if setting_mail_min_date.year < 0:
                    raise Exception
                else:
                    break
            except Exception:
                print('无效选项,请重新输入.', flush=True)
        while True:
            try:
                setting_mail_min_date.month = int(input_option(
                    '输入月份', allow_undefind_input=True, default_option=str(datetime.datetime.now().month), end=':'))
                if setting_mail_min_date.month < 1 or setting_mail_min_date.month > 12:
                    raise Exception
                else:
                    break
            except Exception:
                print('无效选项,请重新输入.', flush=True)
        while True:
            try:
                setting_mail_min_date.day = int(input_option(
                    '输入日期', allow_undefind_input=True, default_option=str(datetime.datetime.now().day), end=':'))
                if setting_mail_min_date.day < 1 or setting_mail_min_date.day > 31:
                    raise Exception
                else:
                    break
            except Exception:
                print('无效选项,请重新输入.', flush=True)

    if input_option('是否设置检索截止日期?', 'y', 'n', default_option='n', end=':') == 'y':
        setting_mail_max_date.enabled = True
        while True:
            try:
                setting_mail_max_date.year = int(input_option(
                    '输入年份', allow_undefind_input=True, default_option=str(datetime.datetime.now().year), end=':'))
                if setting_mail_max_date.year < 0:
                    print('无效选项,请重新输入.', flush=True)
                else:
                    break
            except Exception:
                print('无效选项,请重新输入.', flush=True)
        while True:
            try:
                setting_mail_max_date.month = int(input_option(
                    '输入月份', allow_undefind_input=True, default_option=str(datetime.datetime.now().month), end=':'))
                if setting_mail_max_date.month < 1 or setting_mail_max_date.month > 12:
                    print('无效选项,请重新输入.', flush=True)
                else:
                    break
            except Exception:
                print('无效选项,请重新输入.', flush=True)
        while True:
            try:
                setting_mail_max_date.day = int(input_option(
                    '输入日期', allow_undefind_input=True, default_option=str(datetime.datetime.now().day), end=':'))
                if setting_mail_max_date.day < 1 or setting_mail_max_date.day > 31:
                    print('无效选项,请重新输入.', flush=True)
                else:
                    break
            except Exception:
                print('无效选项,请重新输入.', flush=True)


def operation_parse_file_name(file_name_raw):
    file_name = file_name_raw
    if not os.path.exists(setting_download_path):
        os.makedirs(setting_download_path)
    if os.path.exists(os.path.join(setting_download_path, file_name_raw)):
        i = 2
        dot_index_int = len(
            file_name_raw)-file_name_raw[::-1].find('.')-1 if '.' in file_name_raw else -1
        while True:
            if dot_index_int == -1:
                file_name = file_name_raw + \
                    ' ('+str(i)+')'
            else:
                file_name = '.'.join(
                    [file_name_raw[0:dot_index_int]+'('+str(i)+')', file_name_raw[dot_index_int+1:]])
            if not os.path.exists(os.path.join(setting_download_path, file_name)):
                break
            i += 1
    return file_name


def operation_rollback(file_name_list_raw, file_name=None, largefile_name=None, file_name_tmp=None, largefile_name_tmp=None):
    global file_download_count_global
    if file_name:
        file_name_list_raw.append(file_name)
    if largefile_name:
        file_name_list_raw.append(largefile_name)
    if file_name_tmp:
        if os.path.isfile(os.path.join(setting_download_path, file_name_tmp)):
            os.remove(os.path.join(
                setting_download_path, file_name_tmp))
    if largefile_name_tmp:
        if os.path.isfile(os.path.join(setting_download_path, largefile_name_tmp)):
            os.remove(os.path.join(
                setting_download_path, largefile_name_tmp))
    for file_mixed_name in file_name_list_raw:
        if os.path.isfile(os.path.join(setting_download_path, file_mixed_name)):
            os.remove(os.path.join(
                setting_download_path, file_mixed_name))
            file_download_count_global -= 1


def operation_download_all():
    global thread_state_list_global  # 0:其他;1:读取邮件数据/获取链接;2:下载文件
    global has_thread_state_changed_global
    global thread_list_global, thread_file_name_list_global
    global msg_list_global, msg_total_count_global, msg_processed_count_global
    operation_login_all_imapserver()
    if not len(imap_succeed_index_int_list_global):
        print('E: 无法执行该操作.原因: 没有可用邮箱.', flush=True)
        return
    if setting_allow_manual_input_search_date:
        operation_set_time()
    start_time = time.time()
    if not (setting_mail_min_date.enabled or setting_mail_max_date.enabled):
        if setting_only_search_unseen_mails:
            print('仅检索未读邮件', flush=True)
        else:
            print('检索全部邮件', flush=True)
    else:
        prompt = ''
        prompt += '仅检索日期'
        prompt += ('从 '+setting_mail_min_date.time()
                   ) if setting_mail_min_date.enabled else '在 ' if setting_mail_max_date else ''
        prompt += ' 开始' if setting_mail_min_date.enabled and not setting_mail_max_date.enabled else (str(
            setting_mail_max_date.time()+' 截止')) if not setting_mail_min_date.enabled and setting_mail_max_date.enabled else ' 到 '
        prompt += setting_mail_max_date.time() if setting_mail_min_date.enabled and setting_mail_max_date.enabled else ''
        prompt += '的未读邮件' if setting_only_search_unseen_mails else '的邮件'
        print(prompt, sep='', flush=True)
    for imap_index_int in imap_succeed_index_int_list_global:
        if not (setting_mail_min_date.enabled or setting_mail_max_date.enabled):
            search_command = ''
            if setting_only_search_unseen_mails:
                search_command = 'unseen'
            else:
                search_command = 'all'
        else:
            search_command = ''
            search_command += ('since '+setting_mail_min_date.time()
                               ) if setting_mail_min_date.enabled else ''
            search_command += ' ' if setting_mail_min_date.enabled and setting_mail_max_date.enabled else ''
            search_command += ('before ' + setting_mail_max_date.time()
                               ) if setting_mail_max_date.enabled else ''
            search_command += ' ' if (
                setting_mail_max_date.enabled or setting_mail_min_date.enabled) and setting_only_search_unseen_mails else ''
            search_command += 'unseen' if setting_only_search_unseen_mails else ''
        search_state_last = False
        for i in range(setting_reconnect_max_times+1):
            try:
                typ, data_msg_index_raw = imap_list_global[imap_index_int].search(
                    None, search_command)
                search_state_last = True
                break
            except Exception:
                for i in range(setting_reconnect_max_times):
                    imap_list_global[imap_index_int] = operation_login_imap_server(
                        host[imap_index_int], address[imap_index_int], password[imap_index_int], False)
                    if imap_list_global[imap_index_int] != None:
                        break
        if not search_state_last:
            print('E: 邮箱', address[imap_index_int], '搜索失败,已跳过.', flush=True)
            imap_connect_failed_index_int_list_global.append(
                imap_index_int)
            imap_index_int = None
            continue
        msg_list = list(reversed(data_msg_index_raw[0].split()))
        msg_list_global[imap_index_int] = msg_list
        print(
            '\r邮箱: ', address[imap_index_int], indent(3), sep='', flush=True)
        print(indent(1), '共 ', len(msg_list), ' 封邮件', sep='', flush=True)
    if len(extract_nested_list(msg_list_global)):
        print('共 ', len(extract_nested_list(msg_list_global)),
              ' 封邮件', sep='', flush=True)
    else:
        print('没有符合条件的邮件.\n', flush=True)
        return
    start_time = time.time()
    print('开始处理...\n', end='', flush=True)
    msg_total_count_global = len(extract_nested_list(msg_list_global))
    thread_list_global = []
    thread_state_list_global = [] # -1: 关闭;0: 空闲;1: 处理数据;2: 下载附件
    thread_file_name_list_global = []
    for thread_id in range(setting_thread_count):
        thread_state_list_global.append(0)
        thread_file_name_list_global.append([])
        thread = threading.Thread(
            target=download_thread_func, args=(thread_id,))
        thread_list_global.append(thread)
        thread.daemon = True
        thread.start()
    while True:
        if stop_state_global:
            return
        if thread_state_list_global.count(-1) == len(thread_state_list_global):
            break
        if len(thread_excepion_list_global):
            with lock_var_global:
                raise thread_excepion_list_global.pop(0)
        if has_thread_state_changed_global:
            has_thread_state_changed_global = False
            with lock_print_global:
                print('\r已处理 (', msg_processed_count_global, '/',
                      msg_total_count_global, '),', sep='', end='', flush=True)
                print('线程信息 (', len(thread_state_list_global)-thread_state_list_global.count(-1), '/', len(thread_list_global), ',',
                      thread_state_list_global.count(1), ',', thread_state_list_global.count(2), ')', indent(3), sep='', end='', flush=True)
        time.sleep(0)
    finish_time = time.time()
    with lock_print_global:
        if file_download_count_global > 0:
            print('\r共下载 ', file_download_count_global,
                  ' 个附件', indent(8), sep='', flush=True)
        else:
            print('\r没有可下载的附件', indent(8), flush=True)
        print('耗时: ', round(finish_time-start_time, 2),
              ' 秒', indent(8), sep='', flush=True)
        if len(imap_connect_failed_index_int_list_global):
            print('E: 以下邮箱断开连接,且未能成功连接:', flush=True)
            for imap_connect_failed_index_int in imap_connect_failed_index_int_list_global:
                print(
                    indent(1), address[imap_connect_failed_index_int], sep='', flush=True)
        for msg_list_index_int in range(len(msg_list_global)):
            if len(msg_list_global[msg_list_index_int]) > 0:
                if safe_list_find(imap_fetch_failed_index_int_list_global, msg_list_index_int) == -1:
                    imap_fetch_failed_index_int_list_global.append(
                        msg_list_index_int)
                    for msg in msg_list_global[msg_list_index_int]:
                        msg_fetch_failed_list_global[msg_list_index_int].append(
                            msg)
        if len(imap_fetch_failed_index_int_list_global):
            print('E: 以下邮箱有处理失败的邮件,请尝试重新下载:', flush=True)
            for imap_fetch_failed_index_int in imap_fetch_failed_index_int_list_global:
                print(indent(
                    1), '邮箱: ', address[imap_fetch_failed_index_int], sep='', flush=True)
                print(indent(2), len(
                    msg_fetch_failed_list_global[imap_fetch_failed_index_int]), ' 封邮件处理失败', sep='', flush=True)
        if len(extract_nested_list(msg_download_failed_list_global)):
            msg_download_failed_counted_count = 0
            print('E: 以下邮件有超大附件无法识别或下载失败,请尝试手动下载:', flush=True)
            for imap_download_failed_index_int in imap_download_failed_index_int_list_global:
                print(indent(
                    1), '邮箱: ', address[imap_download_failed_index_int], sep='', flush=True)
                for subject_index_int in range(len(subject_download_failed_list_global[imap_download_failed_index_int])):
                    print(indent(2), msg_download_failed_counted_count+1, ' ',
                          subject_download_failed_list_global[imap_download_failed_index_int][subject_index_int], ' - ', send_time_download_failed_list_global[imap_download_failed_index_int][subject_index_int], sep='', flush=True)
                    msg_download_failed_counted_count += 1
        if len(extract_nested_list(msg_with_undownloadable_attachments_list_global)):
            msg_with_undownloadable_attachments_counted_count = 0
            largefile_undownloadable_link_counted_count = 0
            print('W: 以下邮件的超大附件无法直接下载,但仍可获取链接,请尝试手动下载:', flush=True)
            for imap_with_undownloadable_attachments_index_int in imap_with_undownloadable_attachments_index_int_list_global:
                print(indent(
                    1), '邮箱: ', address[imap_with_undownloadable_attachments_index_int], sep='', flush=True)
                for subject_index_int in range(len(subject_with_undownloadable_attachments_list_global[imap_with_undownloadable_attachments_index_int])):
                    print(indent(2), msg_with_undownloadable_attachments_counted_count+1, ' ',
                          subject_with_undownloadable_attachments_list_global[imap_with_undownloadable_attachments_index_int][subject_index_int], ' - ', send_time_with_undownloadable_attachments_list_global[imap_with_undownloadable_attachments_index_int][subject_index_int], sep='', flush=True)
                    for link_index_int in range(len(largefile_undownloadable_link_list_global[imap_with_undownloadable_attachments_index_int][subject_index_int])):
                        print(indent(3), largefile_undownloadable_link_counted_count+1, ' ',
                              largefile_undownloadable_link_list_global[imap_with_undownloadable_attachments_index_int][subject_index_int][link_index_int], sep='', flush=True)
                        largefile_download_code = largefile_undownloadable_code_list_global[
                            imap_with_undownloadable_attachments_index_int][subject_index_int][link_index_int]
                        if largefile_download_code != 0:
                            print(indent(4), '错误代码: ',
                                  largefile_download_code, sep='', flush=True)
                            if largefile_download_code == 602 or largefile_download_code == -4:
                                print(indent(4), '原因: 文件下载次数达到最大限制.',
                                      sep='', flush=True)
                        largefile_undownloadable_link_counted_count += 1
                    msg_with_undownloadable_attachments_counted_count += 1
            if setting_sign_unseen_tag_after_downloading:
                if input_option('要将以上邮件设为已读吗?', 'y', 'n', default_option='n', end=':') == 'y':
                    msg_with_downloadable_attachments_signed_count = 0
                    print('\r正在标记...', end='', flush=True)
                    for imap_index_int in range(len(imap_list_global)):
                        for msg_index in msg_with_undownloadable_attachments_list_global[imap_index_int]:
                            for i in range(setting_reconnect_max_times+1):
                                try:
                                    imap_list_global[imap_index_int].store(msg_index,
                                                                           'flags', '\\seen')
                                    break
                                except Exception:
                                    for i in range(setting_reconnect_max_times):
                                        imap_list_global[imap_index_int] = operation_login_imap_server(
                                            host[imap_succeed_index_int_list_global[imap_index_int]], address[imap_succeed_index_int_list_global[imap_index_int]], password[imap_succeed_index_int_list_global[imap_index_int]], False)
                                        if imap_list_global[imap_index_int] != None:
                                            break
                            msg_with_downloadable_attachments_signed_count += 1
                    print('\r', indent(6), sep='', end='', flush=True)
                    if not len(extract_nested_list(msg_overdueanddeleted_list_global)):
                        print(flush=True)
                else:
                    if not len(extract_nested_list(msg_overdueanddeleted_list_global)):
                        print(flush=True)
            else:
                if not len(extract_nested_list(msg_overdueanddeleted_list_global)):
                    print(flush=True)
        else:
            if not len(extract_nested_list(msg_overdueanddeleted_list_global)):
                print(flush=True)
        if len(extract_nested_list(msg_overdueanddeleted_list_global)):
            msg_overdueanddeleted_counted_count = 0
            print('\rN: 以下邮件的超大附件全部过期或被删除:', flush=True)
            for imap_overdueanddeleted_index_int in imap_overdueanddeleted_index_int_list_global:
                print(indent(
                    1), '邮箱: ', address[imap_overdueanddeleted_index_int], sep='', flush=True)
                for subject_index_int in range(len(subject_overdueanddeleted_list_global[imap_overdueanddeleted_index_int])):
                    print(indent(2), msg_overdueanddeleted_counted_count+1, ' ',
                          subject_overdueanddeleted_list_global[imap_overdueanddeleted_index_int][subject_index_int], ' - ', send_time_overdueanddeleted_list_global[imap_overdueanddeleted_index_int][subject_index_int], sep='', flush=True)
                    msg_overdueanddeleted_counted_count += 1
            if setting_sign_unseen_tag_after_downloading:
                if input_option('要将以上邮件设为已读吗?', 'y', 'n', default_option='y', end=':') == 'y':
                    msg_overdueanddeleted_signed_count = 0
                    print('\r正在标记...', end='', flush=True)
                    for imap_index_int in range(len(imap_list_global)):
                        for msg_index in msg_overdueanddeleted_list_global[imap_index_int]:
                            for i in range(setting_reconnect_max_times+1):
                                try:
                                    imap_list_global[imap_index_int].store(msg_index,
                                                                           'flags', '\\seen')
                                    break
                                except Exception:
                                    for i in range(setting_reconnect_max_times):
                                        imap_list_global[imap_index_int] = operation_login_imap_server(
                                            host[imap_succeed_index_int_list_global[imap_index_int]], address[imap_succeed_index_int_list_global[imap_index_int]], password[imap_succeed_index_int_list_global[imap_index_int]], False)
                                        if imap_list_global[imap_index_int] != None:
                                            break
                            msg_overdueanddeleted_signed_count += 1
                    print('\r', indent(6), sep='', flush=True)
                else:
                    print(flush=True)
            else:
                print(flush=True)


def operation_fresh_thread_state(thread_id, state):
    global has_thread_state_changed_global
    thread_state_list_global[thread_id] = state
    has_thread_state_changed_global = True


def download_thread_func(thread_id):
    global file_download_count_global, msg_processed_count_global, msg_list_global
    global thread_file_name_list_global
    try:
        for imap_index_int in range(len(imap_succeed_index_int_list_global)):
            if imap_succeed_index_int_list_global[imap_index_int] == None:
                continue
            if not len(msg_list_global[imap_succeed_index_int_list_global[imap_index_int]]):
                continue
            req_state_last = False
            for i in range(setting_reconnect_max_times+1):
                imap = operation_login_imap_server(
                    host[imap_succeed_index_int_list_global[imap_index_int]], address[imap_succeed_index_int_list_global[imap_index_int]], password[imap_succeed_index_int_list_global[imap_index_int]], False)
                if imap != None:
                    break
            if imap != None:
                while True:
                    lock_var_global.acquire()
                    if len(msg_list_global[imap_succeed_index_int_list_global[imap_index_int]]):
                        msg_index = msg_list_global[imap_succeed_index_int_list_global[imap_index_int]].pop(
                            0)
                        lock_var_global.release()
                        file_download_count = 0
                        download_state_last = -1  # -2:下载失败;-1:无附件且处理正常;0:有附件且处理正常;1:有无法直接下载的附件;2:附件全部过期或不存在
                        thread_file_name_list_global[thread_id] = []
                        largefile_undownloadable_code_list = []
                        has_downloadable_attachment = False
                        largefile_downloadable_link_list = []
                        largefile_download_code = 0
                        largefile_undownloadable_link_list = []
                        with lock_var_global:
                            operation_fresh_thread_state(thread_id, 1)
                        fetch_state_last = False
                        for i in range(setting_reconnect_max_times+1):
                            try:
                                typ, data_msg_raw = imap.fetch(
                                    msg_index, 'body.peek[]')
                                fetch_state_last = True
                                break
                            except Exception:
                                for i in range(setting_reconnect_max_times):
                                    imap = operation_login_imap_server(
                                        host[imap_succeed_index_int_list_global[imap_index_int]], address[imap_succeed_index_int_list_global[imap_index_int]], password[imap_succeed_index_int_list_global[imap_index_int]], False)
                                    if imap != None:
                                        break
                        if not fetch_state_last:
                            with lock_print_global:
                                print('E: 有邮件获取失败,已跳过.',flush=True)
                        else:
                            data_msg = email.message_from_bytes(
                                data_msg_raw[0][1])
                            subject = str(header.make_header(
                                header.decode_header(data_msg.get('Subject'))))
                            send_time_raw = str(header.make_header(
                                header.decode_header(data_msg.get('Date'))))[5:]
                            send_time = copy.copy(send_time_raw)
                            try:
                                send_time=str(utils.parsedate_to_datetime(send_time_raw).astimezone(pytz.timezone('Etc/GMT-8')))[:-6]
                            except ValueError:
                                send_time = send_time_raw
                            try:
                                for eachdata_msg in data_msg.walk():
                                    file_name = None
                                    largefile_name = None
                                    file_name_tmp = None
                                    largefile_name_tmp = None
                                    # print(eachdata_msg)
                                    if eachdata_msg.get_content_disposition() and 'attachment' in eachdata_msg.get_content_disposition():
                                        has_downloadable_attachment = True
                                        file_name_raw = str(header.make_header(
                                            header.decode_header(eachdata_msg.get_filename())))
                                        file_data = eachdata_msg.get_payload(
                                            decode=True)
                                        with lock_var_global:
                                            operation_fresh_thread_state(
                                                thread_id, 2)
                                        if stop_state_global:
                                            if setting_rollback_when_download_failed:
                                                with lock_io_global:
                                                    operation_rollback(
                                                        thread_file_name_list_global[thread_id], file_name, largefile_name, file_name_tmp, largefile_name_tmp)
                                            return
                                        lock_io_global.acquire()
                                        file_name_tmp = operation_parse_file_name(
                                            file_name_raw+'.tmp')
                                        with open(os.path.join(setting_download_path, file_name_tmp), 'wb') as file:
                                            lock_io_global.release()
                                            file.write(file_data)
                                        with lock_io_global:
                                            file_name = operation_parse_file_name(
                                                file_name_raw)
                                            os.renames(os.path.join(setting_download_path, file_name_tmp),
                                                    os.path.join(setting_download_path, file_name))
                                        if stop_state_global:
                                            if setting_rollback_when_download_failed:
                                                with lock_io_global:
                                                    operation_rollback(
                                                        thread_file_name_list_global[thread_id], file_name, largefile_name, file_name_tmp, largefile_name_tmp)
                                            return
                                        with lock_print_global, lock_var_global:
                                            print('\r', file_download_count_global+1, ' 已下载 ', file_name, (
                                                ' <- '+file_name_raw)if file_name != file_name_raw else '', indent(8), sep='', flush=True)
                                            print(indent(
                                                1), '邮箱: ', address[imap_succeed_index_int_list_global[imap_index_int]], sep='', flush=True)
                                            print(indent(1), '邮件标题: ', subject, ' - ',
                                                send_time, sep='', flush=True)
                                            file_download_count_global += 1
                                            file_download_count += 1
                                            thread_file_name_list_global[thread_id].append(
                                                file_name)
                                            operation_fresh_thread_state(
                                                thread_id, 0)
                                        if download_state_last == -1 or download_state_last == 2:  # 去除邮件无附件标记或全部过期标记
                                            download_state_last = 0
                                    if eachdata_msg.get_content_type() == 'text/html':
                                        eachdata_msg_charset = eachdata_msg.get_content_charset()
                                        eachdata_msg_data_raw = eachdata_msg.get_payload(
                                            decode=True)
                                        eachdata_msg_data = bytes.decode(
                                            eachdata_msg_data_raw, eachdata_msg_charset)
                                        html_fetcher = BeautifulSoup(
                                            eachdata_msg_data, 'lxml')
                                        if '附件' in eachdata_msg_data:
                                            with lock_var_global:
                                                operation_fresh_thread_state(
                                                    thread_id, 1)
                                            href_list = html_fetcher.find_all('a')
                                            for href in href_list:
                                                if '下载' in href.get_text():
                                                    largefile_downloadable_link = None
                                                    largefile_link = href.get(
                                                        'href')
                                                    if find_childstr_to_list(available_largefile_website_list_global, largefile_link):
                                                        req_state_last = False
                                                        for i in range(setting_reconnect_max_times+1):
                                                            try:
                                                                download_page = requests.get(
                                                                    largefile_link)
                                                                req_state_last = True
                                                                break
                                                            except Exception:
                                                                pass
                                                        if not req_state_last:
                                                            raise Exception
                                                        html_fetcher_2 = BeautifulSoup(
                                                            download_page.text, 'lxml')
                                                        if 'wx.mail.qq.com' in largefile_link:
                                                            script = html_fetcher_2.select_one(
                                                                'body > script:nth-child(2)').get_text()
                                                            largefile_downloadable_link = re.compile(
                                                                r'(?<=var url = ").+(?=")').findall(script)
                                                            if len(largefile_downloadable_link):
                                                                largefile_downloadable_link = largefile_downloadable_link[0].replace(
                                                                    '\\x26', '&')
                                                                largefile_download_method = 0  # get
                                                            else:
                                                                if not has_downloadable_attachment and download_state_last != 1:
                                                                    download_state_last = 2
                                                        elif 'mail.qq.com' in largefile_link:
                                                            largefile_downloadable_link = html_fetcher_2.select_one(
                                                                '#main > div.ft_d_mainWrapper > div > div > div.ft_d_fileToggle.default > a.ft_d_btnDownload.btn_blue')
                                                            if largefile_downloadable_link:
                                                                largefile_downloadable_link = largefile_downloadable_link.get(
                                                                    'href')
                                                                largefile_download_method = 0  # get
                                                            else:
                                                                if not has_downloadable_attachment and download_state_last != 1:
                                                                    download_state_last = 2
                                                        elif 'dashi.163.com' in largefile_link:
                                                            link_key = urllib.parse.parse_qs(
                                                                urllib.parse.urlparse(largefile_link).query)['key'][0]
                                                            req_state_last = False
                                                            for i in range(setting_reconnect_max_times+1):
                                                                try:
                                                                    fetch_result = json.loads(requests.post(
                                                                        'https://dashi.163.com/filehub-master/file/dl/prepare2', json={'fid': '', 'linkKey': link_key}).text)
                                                                    req_state_last = True
                                                                    break
                                                                except Exception:
                                                                    pass
                                                            if not req_state_last:
                                                                raise Exception
                                                            largefile_download_code = fetch_result['code']
                                                            if largefile_download_code == 200:
                                                                largefile_downloadable_link = fetch_result[
                                                                    'result']['downloadUrl']
                                                                largefile_download_method = 0  # get
                                                            elif largefile_download_code == 404 or largefile_download_code == 601:
                                                                if not has_downloadable_attachment and download_state_last != 1:
                                                                    download_state_last = 2
                                                            else:
                                                                largefile_undownloadable_link_list.append(
                                                                    largefile_link)
                                                                largefile_undownloadable_code_list.append(
                                                                    largefile_download_code)
                                                                download_state_last = 1
                                                        elif 'mail.163.com' in largefile_link:
                                                            link_key = urllib.parse.parse_qs(
                                                                urllib.parse.urlparse(largefile_link).query)['file'][0]
                                                            req_state_last = False
                                                            for i in range(setting_reconnect_max_times+1):
                                                                try:
                                                                    fetch_result = json.loads(requests.get(
                                                                        'https://fs.mail.163.com/fs/service', params={'f': link_key, 'op': 'fs_dl_f_a'}).text)
                                                                    req_state_last = True
                                                                    break
                                                                except Exception:
                                                                    pass
                                                            if not req_state_last:
                                                                raise Exception
                                                            largefile_download_code = fetch_result['code']
                                                            if largefile_download_code == 200:
                                                                largefile_downloadable_link = fetch_result[
                                                                    'result']['downloadUrl']
                                                                largefile_download_method = 0  # get
                                                            elif largefile_download_code == -17 or largefile_download_code == -3:
                                                                if not has_downloadable_attachment and download_state_last != 1:
                                                                    download_state_last = 2
                                                            else:
                                                                largefile_undownloadable_link_list.append(
                                                                    largefile_link)
                                                                largefile_undownloadable_code_list.append(
                                                                    largefile_download_code)
                                                                download_state_last = 1
                                                        elif 'mail.sina.com.cn' in largefile_link:
                                                            req_state_last = False
                                                            for i in range(setting_reconnect_max_times+1):
                                                                try:
                                                                    download_page = requests.get(
                                                                        largefile_link)
                                                                    req_state_last = True
                                                                    break
                                                                except Exception:
                                                                    pass
                                                            if not req_state_last:
                                                                raise Exception
                                                            html_fetcher_2 = BeautifulSoup(
                                                                download_page.text, 'lxml')
                                                            can_download = len(
                                                                html_fetcher_2.find_all('input'))
                                                            if can_download:
                                                                largefile_downloadable_link = largefile_link
                                                                largefile_download_method = 1  # post
                                                            else:
                                                                if not has_downloadable_attachment and download_state_last != 1:
                                                                    download_state_last = 2
                                                    elif find_childstr_to_list(unavailable_largefile_website_list_global, largefile_link):
                                                        largefile_undownloadable_link_list.append(
                                                            largefile_link)
                                                        largefile_undownloadable_code_list.append(
                                                            largefile_download_code)
                                                        download_state_last = 1
                                                    elif find_childstr_to_list(website_blacklist, largefile_link):
                                                        continue
                                                    else:
                                                        download_state_last = -2
                                                    if largefile_downloadable_link:
                                                        largefile_downloadable_link_list.append(
                                                            largefile_downloadable_link)
                                                        has_downloadable_attachment = True
                                                        req_state_last = False
                                                        for i in range(setting_reconnect_max_times+1):
                                                            try:
                                                                if largefile_download_method == 0:
                                                                    largefile_data = requests.get(
                                                                        largefile_downloadable_link, stream=True)
                                                                else:
                                                                    largefile_data = requests.post(
                                                                        largefile_downloadable_link, stream=True)
                                                                req_state_last = True
                                                                break
                                                            except Exception:
                                                                pass
                                                        if not req_state_last:
                                                            raise Exception
                                                        largefile_name_raw = largefile_data.headers.get(
                                                            'Content-Disposition')
                                                        largefile_name_raw = largefile_name_raw.encode(
                                                            'ISO-8859-1').decode('utf-8')  # 转码
                                                        largefile_name_raw = largefile_name_raw.split(';')[
                                                            1]
                                                        largefile_name_raw = re.compile(
                                                            r'(?<=").+(?=")').findall(largefile_name_raw)[0]
                                                        with lock_var_global:
                                                            operation_fresh_thread_state(
                                                                thread_id, 2)
                                                        if stop_state_global:
                                                            if setting_rollback_when_download_failed:
                                                                with lock_io_global:
                                                                    operation_rollback(
                                                                        thread_file_name_list_global[thread_id], file_name, largefile_name, file_name_tmp, largefile_name_tmp)
                                                            return
                                                        lock_io_global.acquire()
                                                        largefile_name_tmp = operation_parse_file_name(
                                                            largefile_name_raw+'.tmp')
                                                        req_state_last = False
                                                        for i in range(setting_reconnect_max_times+1):
                                                            try:
                                                                with open(os.path.join(setting_download_path, largefile_name_tmp), 'wb') as file:
                                                                    lock_io_global.release()
                                                                    for largefile_data_chunk in largefile_data.iter_content(1024):
                                                                        if stop_state_global:
                                                                            break
                                                                        file.write(
                                                                            largefile_data_chunk)
                                                                req_state_last = True
                                                                break
                                                            except Exception:
                                                                pass
                                                        if not req_state_last:
                                                            raise Exception
                                                        with lock_io_global:
                                                            largefile_name = operation_parse_file_name(
                                                                largefile_name_raw)
                                                            os.renames(
                                                                os.path.join(setting_download_path, largefile_name_tmp), os.path.join(setting_download_path, largefile_name))
                                                        if stop_state_global:
                                                            if setting_rollback_when_download_failed:
                                                                with lock_io_global:
                                                                    operation_rollback(
                                                                        thread_file_name_list_global[thread_id], file_name, largefile_name, file_name_tmp, largefile_name_tmp)
                                                            return
                                                        with lock_print_global, lock_var_global:
                                                            print('\r', file_download_count_global+1, ' 已下载 ', largefile_name, (
                                                                ' <- '+largefile_name_raw)if largefile_name != largefile_name_raw else '', indent(8), sep='', flush=True)
                                                            print(indent(
                                                                1), '邮箱: ', address[imap_succeed_index_int_list_global[imap_index_int]], sep='', flush=True)
                                                            print(indent(
                                                                1), '邮件标题: ', subject, ' - ', send_time, sep='', flush=True)
                                                            file_download_count_global += 1
                                                            file_download_count += 1
                                                            thread_file_name_list_global[thread_id].append(
                                                                largefile_name)
                                                            operation_fresh_thread_state(
                                                                thread_id, 0)
                                                        if download_state_last == -1 or download_state_last == 2:  # 去除邮件无附件标记或全部过期标记
                                                            download_state_last = 0
                            except Exception as e:
                                if lock_io_global.locked():
                                    lock_io_global.release()
                                with lock_print_global:
                                    if not req_state_last:
                                        print('E: 有附件下载失败,该邮件已跳过.', flush=True)
                                        if setting_rollback_when_download_failed:
                                            operation_rollback(
                                                thread_file_name_list_global[thread_id], file_name, largefile_name, file_name_tmp, largefile_name_tmp)
                                download_state_last = -2
                        with lock_var_global:
                            if fetch_state_last:
                                if download_state_last == 0:
                                    if has_downloadable_attachment:
                                        msg_with_downloadable_attachments_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                            msg_index)
                                        file_name_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                            thread_file_name_list_global[thread_id])
                                        # 防止回滚时把全部下载成功的邮件的附件删除
                                        thread_file_name_list_global[thread_id] = [
                                        ]
                                        if setting_sign_unseen_tag_after_downloading:
                                            for i in range(setting_reconnect_max_times+1):
                                                try:
                                                    if setting_sign_unseen_tag_after_downloading and download_state_last == 0:
                                                        imap.store(msg_index,
                                                                'flags', '\\seen')
                                                    break
                                                except Exception:
                                                    for i in range(setting_reconnect_max_times):
                                                        imap = operation_login_imap_server(
                                                            host[imap_succeed_index_int_list_global[imap_index_int]], address[imap_succeed_index_int_list_global[imap_index_int]], password[imap_succeed_index_int_list_global[imap_index_int]], False)
                                                        if imap != None:
                                                            break
                                elif download_state_last == 1:
                                    if safe_list_find(imap_with_undownloadable_attachments_index_int_list_global, imap_succeed_index_int_list_global[imap_index_int]) == -1:
                                        imap_with_undownloadable_attachments_index_int_list_global.append(
                                            imap_succeed_index_int_list_global[imap_index_int])
                                    msg_with_undownloadable_attachments_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        msg_index)
                                    send_time_with_undownloadable_attachments_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        send_time)
                                    subject_with_undownloadable_attachments_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        subject)
                                    largefile_undownloadable_link_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        largefile_undownloadable_link_list)
                                    largefile_undownloadable_code_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        largefile_undownloadable_code_list)
                                elif download_state_last == 2:
                                    if safe_list_find(imap_overdueanddeleted_index_int_list_global, imap_succeed_index_int_list_global[imap_index_int]) == -1:
                                        imap_overdueanddeleted_index_int_list_global.append(
                                            imap_succeed_index_int_list_global[imap_index_int])
                                    msg_overdueanddeleted_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        msg_index)
                                    send_time_overdueanddeleted_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        send_time)
                                    subject_overdueanddeleted_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        subject)
                                elif download_state_last == -2:
                                    if safe_list_find(imap_download_failed_index_int_list_global, imap_succeed_index_int_list_global[imap_index_int]) == -1:
                                        imap_download_failed_index_int_list_global.append(
                                            imap_succeed_index_int_list_global[imap_index_int])
                                    msg_download_failed_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        msg_index)
                                    send_time_download_failed_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        send_time)
                                    subject_download_failed_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                        subject)
                                msg_processed_count_global += 1
                            else:
                                if safe_list_find(imap_fetch_failed_index_int_list_global, imap_succeed_index_int_list_global[imap_index_int]) == -1:
                                    imap_fetch_failed_index_int_list_global.append(
                                        imap_succeed_index_int_list_global[imap_index_int])
                                msg_fetch_failed_list_global[imap_succeed_index_int_list_global[imap_index_int]].append(
                                    msg_index)
                            operation_fresh_thread_state(thread_id, 0)
                        try:
                            imap.close()
                            imap.logout()
                        except Exception:
                            pass
                    else:
                        lock_var_global.release()
                        break
    except Exception as exception:
        with lock_var_global:
            thread_excepion_list_global.append(exception)
    with lock_var_global:
            operation_fresh_thread_state(thread_id, -1)

def get_path():
    return os.path.dirname(__file__)


def indent(count, unit=4, char=' '):
    placeholder_str = ''
    for i in range(0, count*unit):
        placeholder_str += char
    return placeholder_str


def safe_list_find(List, element):
    try:
        index = List.index(element)
        return index
    except ValueError:
        return -1


def find_childstr_to_list(List, Str):  # 遍历列表,判断列表中字符串是否为指定字符串的子字符串
    for j in List:
        if j in Str:
            return True
    return False


def extract_nested_list(List):
    List2 = copy.deepcopy(List)
    result_list = []
    for i in range(len(List2)):
        if isinstance(List2[i], list) or isinstance(List2[i], tuple):
            result_list += extract_nested_list(List2[i])
        else:
            result_list.append(List2[i])
    return result_list

def input_option(prompt, *options, allow_undefind_input=False, default_option='', end=''):
    if len(options) or len(default_option):
        prompt += ' ('
        for option in options:
            prompt += option
            prompt += '/'
        if len(options):
            prompt = prompt[0:-1]
        if len(default_option):
            if len(options):
                prompt += ','
            prompt += '默认选项:'
            prompt += default_option
        prompt += ')'
    prompt += end
    while True:
        print(prompt, end='', flush=True)
        result = input()
        if not len(result) and len(default_option):
            return default_option
        else:
            if not allow_undefind_input:
                if safe_list_find(options, result) == -1:
                    print('无效选项,请重新输入.', flush=True)
                    continue
            return result


def nexit(code=0,pause=True):
    if pause:
        input_option('按回车键退出 ', allow_undefind_input=True)
    exit(code)


try:
    #读取参数
    #-c: 配置文件路径; -r: 路径相对于程序父目录,否则路径相对于工作目录
    try:
        for opt,val in getopt.getopt(sys.argv[1:],'c:r')[0]:
            if opt=='-c':
                config_custom_path_global=val
            elif opt=='-r':
                is_config_path_relative_to_program_global=True
    except getopt.GetoptError:
        print('F: 程序参数错误.',flush=True)
        nexit(1)

    print('Mail Downloader\nDesingned by Litrix', flush=True)
    print('版本:', _version, flush=True)
    print('获取更多信息,请访问 https://github.com/Litrix2/MailDownloader', flush=True)
    if _mode == 1:
        print('W: 此版本正在开发中,可能包含严重错误,请及时跟进仓库以获取最新信息.')
    elif _mode == 2:
        print('W: 此版本正在测试中,可能不稳定,请及时跟进仓库以获取最新信息.')
    elif _mode == 3:
        print('W: 此版本为演示版本,部分功能与信息显示与正式版本存在差异.')
    print(flush=True)
    config_load_state = operation_load_config()
    while True:
        command = input_option(
            '\r请选择操作 [d:下载;t:测试连接;r:重载配置;n:新建配置;c:清屏;q:退出]', 'd', 't', 'r', 'n', 'c', 'q', default_option='d', end=':')
        if command == 'd' or command == 't':
            if not config_load_state:
                print('E: 未能成功加载配置,请在重新加载后执行该操作.', flush=True)
            else:
                if command == 'd':
                    operation_download_all()
                elif command == 't':
                    operation_login_all_imapserver()
        elif command == 'r':
            config_load_state = operation_load_config()
            operation_load_config_new()
        elif command == 'n':
            if input_option('此操作将生成 config_new.toml,是否继续?', 'y', 'n', default_option='n', end=':') == 'y':
                with open(os.path.join(get_path(), 'config_new.toml'), 'w') as config_new_file:
                    rtoml.dump(config_primary_data, config_new_file,pretty=True)
                print('操作成功完成.', flush=True)
        elif command == 'c':
            Platform = platform.platform().lower()
            if 'windows' in Platform:
                os.system('cls')
            elif 'linux' in Platform or 'macos' in Platform:
                os.system('clear')
            else:
                print('E: 操作系统类型未知,无法执行该操作.', flush=True)
        elif command == 'q':
            break
    nexit(0)
except KeyboardInterrupt:
    stop_state_global = 1
    if 'thread_state_list_global' in vars() and setting_rollback_when_download_failed and thread_state_list_global.count(-1) < setting_thread_count:
        for thread_file_name_list in thread_file_name_list_global:
            with lock_io_global:
                operation_rollback(thread_file_name_list)
    with lock_print_global:
        print('\n强制退出', flush=True)
        time.sleep(0.5)
        nexit(1)
except Exception as e:
    stop_state_global = 1
    with lock_print_global:
        print('\nF: 遇到无法解决的错误.信息如下:', flush=True)
        traceback.print_exc()
        nexit(1)

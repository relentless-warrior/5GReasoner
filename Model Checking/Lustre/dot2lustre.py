
import argparse
import logging
import sys
import io
import itertools as IT
import xml.etree.ElementTree as ET
PY2 = sys.version_info[0] == 2
StringIO = io.BytesIO if PY2 else io.StringIO

# Get an instance of a logger
logger = logging.getLogger(__name__)

class Variable(object):
    def __init__(self, varname, datatype, controltype, initial_value, possible_values, fsm):
        self.varname = varname
        self.datatype = datatype
        self.controltype = controltype
        self.initial_value = initial_value
        self.possible_values = possible_values
        self.fsm = fsm

    def set_varname(self, varname):
        self.varname = varname

    def set_datatype(self, datatype='bool'):
        self.datatype = datatype

    def set_controltype(self, controltype='environment'):
        self.controltype = controltype

class SequenceNumber(object):
    def __init__(self, seqname, start, end, possible_values):
        self.seqname = seqname
        self.start = start
        self.end = end
        self.possible_values = possible_values

class Channel(object):
    def __init__(self, channel_label, start, end, noisy=False):
        self.channel_label = channel_label
        self.start = start
        self.end = end
        self.noisy = noisy

class Action(object):
    def __init__(self, action_label, channel):
        self.action_label = action_label
        self.channel = channel


class Transition(object):
    def __init__(self, transition_label, start, end, condition, actions):
        self.transition_label = transition_label
        self.start = start
        self.end = end
        self.condition = condition
        self.actions = actions
        self.contending_transitions = []
    def set_contending_transitions(self, contending_transitions):
        self.contending_transitions = contending_transitions


class FSM(object):
    def __init__(self, fsm_label, states, init_state, incoming_messages, outgoing_messages, transitions):
        self.fsm_label = fsm_label
        self.states = states
        self.init_state = init_state
        self.incoming_messages = incoming_messages
        self.outgoing_messages = outgoing_messages
        self.transitions = transitions

    def set_states(self,states):
        states = []
        for state in states:
            self.states.append(state)

    def add_state(self,state):
        self.states.append(state)

    def set_actions(self, actions):
        self.actions = []
        for action in actions:
            self.actions.append(action)

    def add_action(self, action):
        self.actions.append(action)

class InjectiveAdversary(object):
    def __init__(self, inj_adv_label, active_channel, alwayson):
        self.inj_adv_label = inj_adv_label
        self.active_channel_label = active_channel
        self.alwayson = alwayson

def parseXML(xmlfile):
    tree = ET.parse(xmlfile)
    # get root element
    root = tree.getroot()

    # store the parsing results
    vars = []
    seq_nums = []
    system_fsms = []
    system_channels = []
    injective_adversaries = []

    # parse variables
    for var in root.iter('VAR'):
        var_label = str(var.attrib['label']).strip()
        datatype = str(var.find('datatype').text).strip()
        controltype = str(var.find('controltype').text).strip()
        initial_value = ''
        possible_values = []
        if(controltype.lower() == 'state'):
            possible_values_list = str(var.find('possiblevalues').text).split(',')
            initial_value = str(var.find('initialvalue').text).strip()
            for i in range(len(possible_values_list)):
                possible_values.append(possible_values_list[i].strip())


        fsm = ''
        if(var.find('fsm') is not None):
            fsm = var.find('fsm').text.strip()

        new_var = Variable(var_label, datatype, controltype, initial_value, possible_values, fsm)
        vars.append(new_var)

    # parse sequence numbers
    for seq in root.iter('seq_num'):
        seq_name = str(seq.find('seq_name').text).strip()
        start = str(seq.find('start').text).strip()
        end = str(seq.find('end').text).strip()
        possible_values = []
        if(seq.find('possiblevalues') is not None):
            possible_values_list = str(seq.find('possiblevalues').text).strip().split(',')

        for i in range(len(possible_values_list)):
            possible_values.append(possible_values_list[i].strip())

        new_seq_num = SequenceNumber(seq_name, start, end, possible_values)
        seq_nums.append(new_seq_num)

    # parse FSMs
    for fsm in root.iter('FSM'):
        fsm_label = str(fsm.attrib['label']).strip()
        # parse states
        states = fsm.find('states')
        fsm_states = []

        # parse states
        for state in states:
            state = str(state.text).strip()
            fsm_states.append(state)

        # initial state of the FSM
        init_state = str(fsm.find('init_state').text).strip()

        # parse transitions
        transitions = fsm.find('transitions')
        fsm_transitions = []
        fsm_null_action_exists = False
        if (fsm.find('transitions')):
            i = 0
            for transition in transitions:
                i = i + 1
                transition_label = str(transition.attrib['label']).strip()
                transition_label = transition_label.split('_')[0] + '_T' + str(i)
                transition.attrib['label'] = transition_label
                tree.write(xmlfile)
                start_state = str(transition.find('start').text).strip()
                end_state = str(transition.find('end').text).strip()
                condition = str(transition.find('condition').text)
                if (end_state not in fsm_states):
                   logger.warn(end_state + ' is not in the list of states of the ' + fsm_label + ' FSM')
                # parse actions
                actions = []
                acts = transition.find('actions')
                for action in acts:
                    action_label = str(action.attrib['label']).strip()
                    chan_label = action.find('channel')
                    chan_label = str(chan_label.attrib['label']).strip()
                    chan_start = str(action.find('channel').find('start').text).strip()
                    chan_end = str(action.find('channel').find('end').text).strip()
                    channel_new = Channel(chan_label,chan_start, chan_end)
                    new_action = Action(action_label, channel_new)
                    actions.append(new_action)

                new_transition = Transition(transition_label, start_state, end_state, condition, actions)
                fsm_transitions.append(new_transition)
                new_fsm = FSM(fsm_label, fsm_states, init_state, fsm_transitions)

        if(not fsm.find('transitions')):
            new_fsm = FSM(fsm_label, fsm_states, init_state,[])

        system_fsms.append(new_fsm)

    # parse channels
    channels = root.find('channels')
    if(root.find('channels')):
        if (channels.find('channel')):
            for channel in channels:
                channel_label = str(channel.attrib['label']).strip()
                # parse a channel
                start = str(channel.find('start').text).strip()
                end = str(channel.find('end').text).strip()
                noisy = str(channel.find('noisy').text).strip()
                new_channel = Channel(channel_label, start, end, noisy)
                system_channels.append(new_channel)

    # parse injective adversaries
    inj_advs = root.find('injective_adversaries')
    if(root.find('injective_adversaries')):
        for inj_adv in inj_advs:
            inj_adv_label = str(inj_adv.attrib['label']).strip()
            # parse inj_adv
            active_channel_label = str(inj_adv.find('activechannel').text).strip()
            alwayson_boolean = str(inj_adv.find('alwayson').text).strip()
            new_injective_adversary = InjectiveAdversary(inj_adv_label, active_channel_label, alwayson_boolean)
            injective_adversaries.append(new_injective_adversary)

    return (vars, seq_nums, system_fsms, system_channels, injective_adversaries)


def parseDOT(dotfile, fsm_label):

    f = open(dotfile, "r")
    lines = f.readlines()

    # store the parsing results
    smv_vars = []
    smv_seq_nums = []
    smv_transitions = []
    smv_manual_checks = []

    system_fsms = []
    system_channels = []
    injective_adversaries = []


    fsm_states = []
    in_msgs = []
    out_msgs = []
    env_vars = []
    state_vars = []
    seq_vars = []
    transitions = []
    transition_counter = 0

    for i in range(len(lines)):
        # state: node [shape = circle, label="ue_rrc_idle"]ue_rrc_idle;

        if 'node' in lines[i]:
            strg = lines[i].split(']')[1].split(';')[0].strip()
            fsm_states.append(strg.strip())
            #print 'state = ', strg.strip()

        # //initial_state: ue_rrc_idle
        elif 'initial_state' in lines[i]:
            init_state = lines[i].split(':')[1].strip()
            #print 'init state = ', init_state

        #//incoming messages: rrc_release, rrc_reject, rrc_setup, rrc_suspend, rrc_sm_command, rrc_reconf, rrc_reestab, rrc_resume, paging_tmsi, paging_icrnti, dl_info_transfer, rrc_resume;
        elif 'incoming messages' in lines[i]:
            strg = lines[i].split(':')[1].split(';')
            for s in strg:
                s = s.strip()
                if s is None or s is '':
                        break
                in_msgs.append(s.strip())
                #print 'in_msg = ', s.strip()

        #//outgoing messages: rrc_setup_req, rrc_setup_complete, rrc_sm_complete, rrc_sm_failure, rrc_reconf_complete, rrc_reestab_req, rrc_reestab_complete, ul_info_transfer, rrc_resume_req, rrc_resume_complete;
        elif 'outgoing messages' in lines[i]:
            strg = lines[i].split(':')[1].split(';')
            for s in strg:
                s = s.strip()
                if s is None or s is '':
                        break
                out_msgs.append(s.strip())
                #print 'out_msg = ', s.strip()

        #//environment variables: nas_requested_con_establishment, smc_mac_failure, reconf_mac_failure, ul_transfer_required, dl_transfer_mac_failure, resume_mac_failure, suspend_mac_failure, reestab_setup_mac_failure;
        elif 'environment variables' in lines[i]:
            strg = lines[i].split(':')[1].split(';')
            for s in strg:
                s = s.strip()
                if s is None or s is '':
                        break
                if "{" not in s:
                    env_var = s.strip()
                    env_vars.append(env_var)
                    new_var = Variable(env_var, 'bool', 'environment', None, None, fsm_label)
                    smv_vars.append(new_var)
                else:
                    var_label = s.split("{")[0].strip()
                    values = s.split("{")[1].split("}")[0]
                    possible_values = []
                    values = values.split(',')
                    for v in values:
                        possible_values.append(v.strip())
                    init_value = s.split('<')[1].split('>')[0].strip()
                    new_var = Variable(var_label, 'enumerate', 'environment', init_value, possible_values, fsm_label)
                    smv_vars.append(new_var)
                #print 'env_var = ', env_var

        #//state variables: rrc_sec_ctx_exist{true, false}<false>;
        elif 'state variables' in lines[i]:
            vars = lines[i].split(':')[1].split(';')
            for v in vars:
                v = v.strip()
                if v is None or v is '':
                    break

                state_tokens = v.strip()

                strg = state_tokens.split('{')

                state_var_label = strg[0].strip() # strg[1]: true, false}<false>
                state_vars.append(state_var_label)

                values = strg[1].split('}')


                possible_values = []
                strg = values[0].split(',') # values[1]:<false>
                for s in strg:
                    if 'true' in s.strip().lower():
                        possible_values.append('TRUE')
                    elif 'false' in s.strip().lower():
                        possible_values.append('FALSE')
                    else:
                        possible_values.append(s.strip())

                #print 'possible_values = ', possible_values
                init_value = values[1].split('<')
                init_value = init_value[1].split('>')[0].strip()
                if 'TRUE' in possible_values:
                    if 'true' in init_value.lower():
                        init_value = 'true'
                    elif 'false' in init_value.lower():
                        init_value = 'false'
                    #print 'init value = ', init_value
                    new_var = Variable(state_var_label, 'bool', 'state', init_value.lower(), possible_values, fsm_label)
                else:
                    #new_var = Variable(state_var_label, 'enumerate', 'state', init_value.lower(), possible_values, fsm_label)
                    new_var = Variable(state_var_label, 'enumerate', 'state', init_value, possible_values, fsm_label)
                smv_vars.append(new_var)

        #//sequence variables: rrc_sec_ctx{0,6}<((rrc_sec_ctx + 1) mod 7), 0>;
        elif 'sequence variables' in lines[i]:
            vars = lines[i].split(':')[1].split(';')

            for v in vars:
                v = v.strip()
                if v is None or v is '':
                    break

                seq_tokens = v.strip()


                strg = seq_tokens.split('{')
                seq_var_label = strg[0].strip()  # str[1]: 0,6}<((rrc_sec_ctx + 1) mod 7), 0>
                seq_vars.append(seq_var_label)


                values = strg[1].split('}')
                strg = values[0].split(',')  # values[1]:<((rrc_sec_ctx + 1) mod 7), 0>
                start = strg[0]
                end = strg[1]

                init_values = values[1].split('<')
                init_values = init_values[1].split('>')[0].strip()
                init_values = init_values.split(',')
                possible_values = []
                for iv in init_values:
                    possible_values.append(iv.strip())
                if (seq_var_label in 'ue_seq'):
                    print '========== ue_seq: possible_values = ', possible_values, ' =============='

                new_seq_num = SequenceNumber(seq_var_label, start, end, possible_values)
                smv_seq_nums.append(new_seq_num)

                # //state variables: rrc_sec_ctx_exist{true, false}<false>;
        elif 'define' in lines[i]:
            checks = lines[i].split(":", 1)
            checks = checks[1].split(';')
            print 'checks =', checks
            for check in checks:
                check = check.strip()
                if v is None or v is '':
                    break
                smv_manual_checks.append(check.lstrip())
        # transition
        # ue_rrc_idle -> ue_rrc_setup_requested [label = "nas_requested_con_establishment | paging_tmsi /
        #     rrc_setup_req, rrc_sec_ctx_exist=false"];
        elif '//' in lines[i] and lines[i].startswith('//'):
            continue

        elif '->' in lines[i]:
            transition = ''
            strg = lines[i].split('->')
            start_state = strg[0].strip() # str[1]: ue_rrc_setup_requested [label = "nas_requested_con_establishment | paging_tmsi /

            strg = strg[1].split('[')
            end_state = strg[0].strip() # str[1]: label = "nas_requested_con_establishment | paging_tmsi /


            if start_state not in fsm_states:
                print lines[i]
                print 'ERROR: start_state is not in the list of states'
                return

            if end_state not in fsm_states:
                print 'states = ', state_vars
                print 'end_state ', end_state
                print 'ERROR: end_state is not in the list of states'
                return

            strg = strg[1].split('"')
            if len(strg) == 3:  #transition is written in one line
                transition = strg[1]

            else:
                transition = strg[1].strip()
                #print transition
                j = i+1
                while '"]' not in lines[j].strip():
                    transition = transition + lines[j].strip()
                    #print transition
                    j = j + 1
                strg = lines[j].split('"]')
                transition = transition + strg[0]
                i = j
                transitions.append(transition)

            transition_counter = transition_counter + 1
            #transition_counter = 0
            transition_label = fsm_label + "_T" + str(transition_counter)

            values = transition.split('/')
            #print 'values = ', values

            cond_str = values[0]
            act_str = values[1]

            # PARSING ACTIONS
            acts = act_str.split(',')
            actions = []
            for act in acts:
                action_label = act.strip()
                if action_label == '':
                    print 'ERROR: There are some transitions in comments (//) or missing underscore sign or extra comma due to which empty action is happening????'
                    print lines[i]
                    continue

                if action_label == '_':
                    action_label = 'null_action'

                if action_label in out_msgs:
                    if 'ue' in fsm_label.lower() and 'rrc' in fsm_label.lower():
                        chan_label = 'chan_UB'
                        chan_start = 'UE_RRC'
                        chan_end = 'BS_RRC'
                    elif 'ue' in fsm_label.lower() and 'nas' in fsm_label.lower():
                        chan_label = 'chan_UA'
                        chan_start = 'UE_NAS'
                        chan_end = 'AMF_NAS'
                    elif 'bs' in fsm_label.lower() and 'rrc' in fsm_label.lower():
                        chan_label = 'chan_BU'
                        chan_start = 'BS_RRC'
                        chan_end = 'UE_RRC'
                    elif 'amf' in fsm_label.lower() and 'nas' in fsm_label.lower():
                        chan_label = 'chan_AU'
                        chan_start = 'AMF_NAS'
                        chan_end = 'UE_NAS'
                    #print 'action_label', action_label


                else:
                    #print 'internal_action: ', action_label
                    for out_msg in out_msgs:
                        if out_msg == action_label:
                            print 'ERROR: Outgoing message has been parsed as ACTION????????'

                    if '=' in action_label:
                        int_act_tokens = action_label.split('=')
                        int_act = int_act_tokens[0].strip()
                        value = int_act_tokens[1].strip().lstrip()
                        #print 'value = ', value
                        if 'true' in value:
                            action_label = action_label.replace('true', 'true')
                        elif 'false' in value:
                            action_label = action_label.replace('false', 'false')
                        #print 'action_label =', action_label

                    elif '++' in action_label:
                        int_act_tokens = action_label.split('++')
                        int_act = int_act_tokens[0].strip()
                        action_label = '(' + int_act + '=' + int_act + '+ 1)'
                    chan_label = 'internal'

                    if 'ue' in fsm_label.lower():
                        chan_start = 'UE'
                        chan_end = 'UE'
                    elif 'bs' in fsm_label.lower():
                        chan_start = 'BS'
                        chan_end = 'BS'
                    elif 'amf' in fsm_label.lower():
                        chan_start = 'AMF'
                        chan_end = 'AMF'

                if(action_label != '' and action_label != None):
                    #print "*** ACTION LABEL = ", action_label + ' ****'
                    channel_new = Channel(chan_label, chan_start, chan_end)
                    new_action = Action(action_label, channel_new)
                    actions.append(new_action)

            # PARSING CONDITIONS
            condition = cond_str
            # if 'paging_tmsi' in condition:
            #     print 'condition = ', condition
            # print 'condition = ', condition
            #
            cond_tokens = cond_str.split(' ')

            # if 'paging_tmsi' in condition:
            #     print 'cond tokens = ', cond_tokens
            #     print 'condition = ', condition

            for token in cond_tokens:
                token = token.strip()
                if '(' in token:
                    token = token.split('(')[1]
                if ')' in token:
                    token = token.split(')')[0]

                if token in in_msgs:
                    if 'ue' in fsm_label.lower() and 'rrc' in fsm_label.lower():
                        #msg_prefix = 'chan_BU=chanBU_'
                        msg_prefix = 'BS_RRC_message=BS_RRC_'
                    elif 'ue' in fsm_label.lower() and 'nas' in fsm_label.lower():
                        #msg_prefix = 'chan_AU = chanAU_'
                        msg_prefix = 'AMF_NAS_message=AMF_NAS_'
                    elif 'bs' in fsm_label.lower() and 'rrc' in fsm_label.lower():
                        #msg_prefix = 'chan_UB=chanUB_'
                        msg_prefix = 'UE_RRC_message=UE_RRC_'
                    elif 'amf' in fsm_label.lower() and 'nas' in fsm_label.lower():
                        #msg_prefix = 'chan_UA=chanUA_'
                        msg_prefix = 'UE_NAS_message=UE_NAS_'

                    msg = msg_prefix + token
                    condition = condition.replace(token, msg)
                    condition = condition.replace('TRUE', 'true')
                    condition = condition.replace('FALSE', 'false')
            #print 'Modified condition: ' + condition
            new_transition = Transition(transition_label, start_state, end_state, condition, actions)
            smv_transitions.append(new_transition)

    fsm = FSM(fsm_label, fsm_states, init_state, in_msgs, out_msgs, smv_transitions)

    print 'states = ', fsm_states
    print 'incoming messages =', in_msgs
    print 'outgoing messages = ', out_msgs
    print 'environment variables = ', env_vars
    print 'state vars = ', state_vars
    # print 'Transitions = '
    # for transition in smv_transitions:
    #     print transition.condition


    f.close()
    return (env_vars, state_vars, seq_vars, smv_vars, smv_seq_nums, fsm, smv_manual_checks)


def create_vars(vars_client, vars_server):
    vars = []
    for var in vars_client:
        vars.append(var)
    for var in vars_server:
        vars.append(var)
    return vars

def create_seq_nums(client_seq_nums, server_seq_nums):
    seq_nums = []
    for seq_num in client_seq_nums:
        seq_nums.append(seq_num)
    for seq_num in server_seq_nums:
        seq_nums.append(seq_num)
    return seq_nums

def create_fsms (fsm_client, fsm_server):
    fsms = []
    fsms.append(fsm_client)
    fsms.append(fsm_server)
    return fsms

def create_channels(client_fsm_label, server_fsm_label):
    channels = []
    injective_adversaries = []
    if 'ue' in client_fsm_label.lower() and 'rrc' in client_fsm_label.lower():
        channel1 = Channel('chan_UB', 'UE_RRC', 'BS_RRC')
        channel2 = Channel('chan_BU', 'BS_RRC', 'UE_RRC')
        channels.append(channel1)
        channels.append(channel2)
        injective_adversary1 = InjectiveAdversary('inj_adv_UB', 'chan_UB' , True)
        injective_adversary2 = InjectiveAdversary('inj_adv_BU', 'chan_BU', True)
        injective_adversaries.append(injective_adversary1)
        injective_adversaries.append(injective_adversary2)
    elif 'ue' in client_fsm_label.lower() and 'nas' in client_fsm_label.lower():
        channel1 = Channel('chan_UA', 'UE_NAS', 'AMF_NAS')
        channel2 = Channel('chan_AU', 'AMF_NAS', 'UE_NAS')
        channels.append(channel1)
        channels.append(channel2)
        injective_adversary1 = InjectiveAdversary('inj_adv_UA', 'chan_UA', True)
        injective_adversary2 = InjectiveAdversary('inj_adv_AU', 'chan_AU', True)
        injective_adversaries.append(injective_adversary1)
        injective_adversaries.append(injective_adversary2)
    return channels, injective_adversaries

def compile_manual_checks(client_checks, server_checks):
    checks = []
    if client_checks is not None and len(client_checks)!=0:
        for c in client_checks:
            checks.append(c)
    if server_checks is not None and len(server_checks) != 0:
        for c in server_checks:
            checks.append(c)
    return checks

def dump_states(outputFile, system_fms):
    outputFile.write('---- STATES ----\n')

    for fsm in system_fms:
        outputFile.write('---- {0} states ----\n'.format(fsm.fsm_label))
        outputFile.write('type {0}_states = enum{{\n'.format(fsm.fsm_label))
        for i in range(len(fsm.states)):
            if i < len(fsm.states) - 1:
                outputFile.write('\t{0},\n'.format(str(fsm.states[i])))
            else:
                outputFile.write('\t{0}\n'.format(str(fsm.states[i])))
        outputFile.write('};\n')

def dump_enumerate_variables(outputFile, vars):
    outputFile.write('---- ENUMERATE VARIABLES ----\n')

    for var in vars:
        if 'enumerate' not in var.datatype:
            continue
        outputFile.write('---- {0} ----\n'.format(var.varname))
        outputFile.write('type {0}_enum = enum{{\n'.format(var.varname))
        for i in range(len(var.possible_values)):
            if i < len(var.possible_values) - 1:
                outputFile.write('\t{0},\n'.format(var.possible_values[i]))
            else:
                outputFile.write('\t{0}\n'.format(var.possible_values[i]))
        outputFile.write('};\n')

def dump_transition_enum(outputFile, fsms):
    outputFile.write('---- MESSAGES ----\n')
    for fsm in fsms:
        outputFile.write('type {0}_transitions = enum{{'.format(fsm.fsm_label))

        ctr = 0
        for transition in fsm.transitions:
            if ctr % 10 == 0:
                outputFile.write('\n\t{0} , '.format(transition.transition_label))
            else:
                outputFile.write('{0} , '.format(transition.transition_label))

            ctr += 1

        outputFile.write('{0}_null_transition\n'.format(fsm.fsm_label))
        outputFile.write('};\n')

def dump_messages(outputFile, fsms):
    outputFile.write('---- MESSAGES ----\n')
    def dump_message_enum(fsm_label, possible_values):
        outputFile.write('---- {0} outgoing messages ----\n'.format(fsm_label))
        outputFile.write('type {0}_messages = enum{{\n'.format(fsm_label))
        for i in range(len(possible_values)):
            if i < len(possible_values) - 1:
                outputFile.write('\t{0}_{1},\n'.format(fsm_label, possible_values[i]))
            else:
                outputFile.write('\t{0}_{1}\n'.format(fsm_label, possible_values[i]))
        outputFile.write('};\n')
    fsm_1 = fsms[0]
    fsm_2 = fsms[1]

    if not (set(fsm_1.incoming_messages) == set(fsm_2.outgoing_messages)) \
            or not (set(fsm_1.outgoing_messages) == set(fsm_2.incoming_messages)):
        print 'ERROR: Incoming messages does not equal the outgoing messages from the other state machine'
    dump_message_enum(fsm_1.fsm_label, fsm_1.outgoing_messages)
    dump_message_enum(fsm_2.fsm_label, fsm_2.outgoing_messages)

def parse_condition(condition, vars):
    condition = " ".join(condition.split())
    condition = condition.replace('amf_wait_for = ', 'amf_wait_for=')
    condition = condition.replace('&', ' & ')
    condition = condition.replace('! ', '!')
    condition = condition.replace('|', '| ')
    condition = condition.replace('(', '( ')
    def parse_item(item):
        if item == '&':
            return 'and'
        elif item == '|':
            return 'or'
        elif item.startswith('!'):
            inner_item = parse_condition(item.split('!')[1], vars)
            return 'not({0})'.format(inner_item)
        else:
            return item
    condition_list = condition.split()
    condition_list = list(map(parse_item, condition_list))
    return " ".join(condition_list)

def dump_helper_nodes(outputFile):
    outputFile.write('''
-- Happened: Returns true iff X was ever true
node Happened(X : bool) 
returns (Y : bool);
let  
	Y = X or (false -> pre Y);
tel

-- HeldSinceBeginning: Returns true iff x has been true since beginning
node HeldSinceBeginning (X : bool)
returns (Y : bool;)
let
	Y = not Happened(not(X));
tel
    ''')

def dump_transition_node(outputFile, fsm, other_fsm_label, vars, manual_checks):
    checks = [check.split(':=')[0].strip() for check in manual_checks if 'check' in check]
    outputFile.write('\n---- Transition Node ----\n')

    fsm_vars = [var for var in vars if var.fsm == fsm.fsm_label]

    fsm_environment_vars = [var for var in fsm_vars if var.controltype == 'environment']
    fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']

    outputFile.write('node {0} (\n'.format(fsm.fsm_label))
    outputFile.write('\t{0}_prev_state : {0}_states;\n'.format(fsm.fsm_label))
    outputFile.write('\t{0}_message : {0}_messages;\n'.format(other_fsm_label))

    for var in fsm_environment_vars:
        if var.datatype == 'enumerate':
            outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
        else:
            outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

    for var in fsm_state_vars:
        if var.datatype == 'enumerate':
            outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
        else:
            outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

    for check in checks:
        outputFile.write('\t{0} : bool;\n'.format(check))

    if 'UE' in fsm.fsm_label and "NAS" in fsm.fsm_label:
        outputFile.write('\t{0} : int;\n'.format("ue_nas_dl_count"))

    outputFile.write(')\n')

    outputFile.write('returns (\n')
    outputFile.write('\t{0}_transition : {0}_transitions;\n'.format(fsm.fsm_label))
    outputFile.write(')\n')

    outputFile.write('let\n')
    outputFile.write('\t{0}_transition = \n'.format(fsm.fsm_label))

    ctr = 0
    for transition in fsm.transitions:
        if ctr == 0:
            outputFile.write('\tif (\n')
            ctr += 1
        else:
            outputFile.write('\telse if (\n')

        starting_state = transition.start
        if starting_state == 'any_state':
            outputFile.write('\t\t(\n')
            states = [fsm.fsml_label + '_prev_state = {0}'.format(state) for state in fsm.states]
            outputFile.write('\t\t' + 'or'.join(states) + '\n')
        else:
            outputFile.write('\t\t{0}_prev_state = {1} and \n'.format(fsm.fsm_label, transition.start))

        condition = '\t\t{0}'.format(parse_condition(transition.condition, vars))
        condition = condition.replace("regrejectreUE_NAS_message=UE_NAS_reg_required", "regrejectrereg_required")
        if "regrejectreUE_NAS_message=UE_NAS_reg_required" in condition:
            print condition
        outputFile.write(condition)
        #outputFile.write('\t\t{0}'.format(parse_condition(transition.condition, vars)))
        outputFile.write('\n\t) then\n')
        outputFile.write('\t\t{0}\n'.format(transition.transition_label))

    outputFile.write('\telse\n\t\t{0}_null_transition;\n'.format(fsm.fsm_label))

    outputFile.write('tel\n')


def dump_controller_contract(outputFile, fsm, other_fsm_label, vars, manual_checks, sequence_nums):
    checks = [check.split(':=')[0].strip() for check in manual_checks if 'check' in check]
    outputFile.write('\n---- Controller Contract Node ----\n')

    fsm_vars = [var for var in vars if var.fsm == fsm.fsm_label]

    fsm_environment_vars = [var for var in fsm_vars if var.controltype == 'environment']
    fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']

    outputFile.write('contract {0}_controller_contract (\n'.format(fsm.fsm_label))
    outputFile.write('\t{0}_message : {0}_messages;\n'.format(other_fsm_label))

    if fsm.fsm_label == 'UE_NAS':
        outputFile.write('\tamf_ue_shared_seq : int;\n')

    for var in fsm_environment_vars:
        if var.datatype == 'enumerate':
            outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
        else:
            outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

    #if 'UE' in fsm.fsm_label:
    #    outputFile.write('\t{0} : int;\n'.format("previous_ue_nas_dl_count"))

    outputFile.write(')\n')

    ### RETURN STARTS HERE
    outputFile.write('returns (\n')
    outputFile.write('\t{0}_state : {0}_states;\n'.format(fsm.fsm_label))
    outputFile.write('\t{0}_message : {0}_messages;\n'.format(fsm.fsm_label))

    if fsm.fsm_label == 'AMF_NAS':
        outputFile.write('\t{0} : int;\n'.format('amf_ue_shared_seq'))

    for seq_num in sequence_nums:
        if seq_num.seqname == 'amf_ue_shared_seq':
            continue
        outputFile.write('\t{0} : int;\n'.format(seq_num.seqname))

    for var in fsm_state_vars:
        if var.datatype == 'enumerate':
            outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
        else:
            outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

    for check in checks:
        outputFile.write('\t{0} : bool;\n'.format(check))

    outputFile.write('\t{0}_transition : {0}_transitions;\n'.format(fsm.fsm_label))
    outputFile.write(');\n')

    outputFile.write('let\n')

    if fsm.fsm_label == 'UE_NAS':

        with open("properties-guarantees/UE_NAS_guarantees.txt") as f:
            lines = f.readlines()
            outputFile.writelines(lines)

    if fsm.fsm_label == 'UE_RRC':

        with open("properties-guarantees/UE_RRC_guarantees.txt") as f:
            lines = f.readlines()
            outputFile.writelines(lines)

    else:
        outputFile.write('\tguarantee "g1" true;\n')

    outputFile.write('tel\n')


def dump_controller_contract_signature(outputFile, fsm, other_fsm_label, vars, manual_checks, sequence_nums):
    checks = [check.split(':=')[0].strip() for check in manual_checks if 'check' in check]
    outputFile.write('\n---- Controller Contract Node ----\n')

    fsm_vars = [var for var in vars if var.fsm == fsm.fsm_label]

    fsm_environment_vars = [var for var in fsm_vars if var.controltype == 'environment']
    fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']

    outputFile.write('(*@contract import\n')
    outputFile.write('{0}_controller_contract (\n'.format(fsm.fsm_label))
    outputFile.write('\t{0}_message,\n'.format(other_fsm_label))

    if fsm.fsm_label == 'UE_NAS':
        outputFile.write('\tamf_ue_shared_seq,\n')

    ctr = 0
    for var in fsm_environment_vars:
        if var.datatype == 'enumerate':
            if ctr == len(fsm_environment_vars) - 1:
                outputFile.write('\t{0}\n'.format(var.varname))
            else:
                outputFile.write('\t{0},\n'.format(var.varname))

        else:
            if 'UE' in fsm.fsm_label:
                if ctr == len(fsm_environment_vars) - 1:
                    outputFile.write('\t{0}\n'.format(var.varname))
                else:
                    outputFile.write('\t{0},\n'.format(var.varname))
            else:
                if ctr == len(fsm_environment_vars) - 1:
                    outputFile.write('\t{0}\n'.format(var.varname))
                else:
                    outputFile.write('\t{0},\n'.format(var.varname))

        ctr += 1

    #if 'UE' in fsm.fsm_label:
    #    outputFile.write('\t{0}\n'.format("previous_ue_nas_dl_count"))

    outputFile.write(')\n')

    ### RETURN STARTS HERE
    outputFile.write('returns (\n')
    outputFile.write('\t{0}_state,\n'.format(fsm.fsm_label))
    outputFile.write('\t{0}_message,\n'.format(fsm.fsm_label))

    if fsm.fsm_label == 'AMF_NAS':
        outputFile.write('\t{0},\n'.format('amf_ue_shared_seq'))

    for seq_num in sequence_nums:
        if seq_num.seqname == 'amf_ue_shared_seq':
            continue
        outputFile.write('\t{0},\n'.format(seq_num.seqname))

    for var in fsm_state_vars:
        outputFile.write('\t{0},\n'.format(var.varname))

    for check in checks:
        outputFile.write('\t{0},\n'.format(check))

    outputFile.write('\t{0}_transition\n'.format(fsm.fsm_label))
    outputFile.write(');\n')
    outputFile.write('*)\n')

def dump_controller_node(outputFile, fsm, other_fsm_label, vars, manual_checks, sequence_nums):
    checks = [check.split(':=')[0].strip() for check in manual_checks if 'check' in check]
    outputFile.write('\n---- Controller Node ----\n')

    fsm_vars = [var for var in vars if var.fsm == fsm.fsm_label]

    fsm_environment_vars = [var for var in fsm_vars if var.controltype == 'environment']
    fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']

    outputFile.write('node {0}_controller (\n'.format(fsm.fsm_label))
    outputFile.write('\t{0}_message : {0}_messages;\n'.format(other_fsm_label))

    if fsm.fsm_label == 'UE_NAS':
        outputFile.write('\tamf_ue_shared_seq : int;\n')

    for var in fsm_environment_vars:
        if var.datatype == 'enumerate':
            outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
        else:
            outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

    outputFile.write(')\n')

    ### RETURN STARTS HERE
    outputFile.write('returns (\n')
    outputFile.write('\t{0}_state : {0}_states;\n'.format(fsm.fsm_label))
    outputFile.write('\t{0}_message : {0}_messages;\n'.format(fsm.fsm_label))

    if fsm.fsm_label == 'AMF_NAS':
        outputFile.write('\t{0} : int;\n'.format('amf_ue_shared_seq'))

    for seq_num in sequence_nums:
        if seq_num.seqname == 'amf_ue_shared_seq':
            continue
        outputFile.write('\t{0} : int;\n'.format(seq_num.seqname))

    for var in fsm_state_vars:
        if var.datatype == 'enumerate':
            outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
        else:
            outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

    for check in checks:
        outputFile.write('\t{0} : bool;\n'.format(check))

    outputFile.write('\t{0}_transition : {0}_transitions;\n'.format(fsm.fsm_label))
    outputFile.write(')\n')

    dump_controller_contract_signature(outputFile, fsm, other_fsm_label, vars, manual_checks, sequence_nums)

    # HELPER VARIABLES
    if fsm.fsm_label == 'UE_NAS':
        outputFile.write('\tvar range : int;\n')

    # BODY OF NODE STARTS HERE
    # Updates the variables
    outputFile.write('let\n')
    outputFile.write('\t{0}_transition = {0}(\n'.format(fsm.fsm_label))
    outputFile.write('\t\t{0} -> pre {1}_state,\n'.format(fsm.init_state, fsm.fsm_label))
    outputFile.write('\t\t{0}_message,\n'.format(other_fsm_label))

    for var in fsm_environment_vars:
        outputFile.write('\t\t{0},\n'.format(var.varname))

    if 'NAS' in fsm.fsm_label:
        for var in fsm_state_vars:
            outputFile.write('\t\t{0} -> pre {1},\n'.format(var.initial_value, var.varname))
    else:
        ctr = 0
        for var in fsm_state_vars:
            if ctr < len(fsm_state_vars) - 1:
                outputFile.write('\t\t{0} -> pre {1},\n'.format(var.initial_value, var.varname))
            else:
                outputFile.write('\t\t{0} -> pre {1}\n'.format(var.initial_value, var.varname))
            ctr += 1

    ctr = 0
    for check in checks:
        if 'UE' in fsm.fsm_label:
            if ctr < len(checks) - 1:
                outputFile.write('\t\ttrue -> pre {0},\n'.format(check))
            else:
                outputFile.write('\t\ttrue -> pre {0},\n'.format(check))
        else:
            if ctr < len(checks) - 1:
                outputFile.write('\t\ttrue -> pre {0},\n'.format(check))
            else:
                outputFile.write('\t\ttrue -> pre {0}\n'.format(check))
        ctr += 1

    if 'UE_NAS' in fsm.fsm_label:
        outputFile.write('\t\t0 -> pre {0}'.format("ue_nas_dl_count"))

    outputFile.write('\t);\n')


    # Updates state
    transition_to_state_map = dict()
    for transition in fsm.transitions:
        end_state = transition.end
        if end_state in transition_to_state_map:
            transition_to_state_map[end_state].append(transition.transition_label)
        else:
            transition_to_state_map[end_state] = [transition.transition_label]
    outputFile.write('\t{0}_state = \n'.format(fsm.fsm_label))
    ctr = 0
    for state in transition_to_state_map:
        if ctr == 0:
            outputFile.write('\t\tif (\n')
        elif ctr == len(transition_to_state_map) - 1:
            outputFile.write('\t\telse\n\t\t\t{0};\n'.format(state))
            continue
        else:
            outputFile.write('\t\telse if (\n')

        ctr += 1
        transitions = transition_to_state_map[state]
        transitions = ['{0}_transition = {1}'.format(fsm.fsm_label, transition) for transition in transitions]
        outputFile.write('\t\t\t' + ' or '.join(transitions) + '\n\t\t\t)\n')
        outputFile.write('\t\t\tthen {0}\n'.format(state))

    # Updates message to return
    transition_to_message_map = dict()
    for transition in fsm.transitions:
        message_being_sent = False
        for action in transition.actions:
            if action.action_label in fsm.outgoing_messages:
                message_being_sent = True
                if action.action_label in transition_to_message_map:
                    transition_to_message_map[action.action_label].append(transition.transition_label)
                else:
                    transition_to_message_map[action.action_label] = [transition.transition_label]
                continue
        if not message_being_sent:
            action_label = 'null_action'
            if action_label in transition_to_message_map:
                transition_to_message_map[action_label].append(transition.transition_label)
            else:
                transition_to_message_map[action_label] = [transition.transition_label]
    outputFile.write('\t{0}_message = \n'.format(fsm.fsm_label))
    ctr = 0
    for key in transition_to_message_map.keys():
        if "null_action" in key:
            continue
        if ctr == 0:
            outputFile.write('\t\tif (\n')
        else:
            outputFile.write('\t\telse if (\n')

        ctr += 1
        transitions = transition_to_message_map[key]
        transitions = [fsm.fsm_label + '_transition = ' + transition for transition in transitions]
        outputFile.write('\t\t\t' + " or ".join(transitions) + '\n\t\t\t)\n')
        outputFile.write('\t\t\tthen ' + fsm.fsm_label + '_' + key + '\n')
    outputFile.write("\t\telse " + fsm.fsm_label + '_null_action;\n\n')

    for var in fsm_state_vars:
        if var.datatype != 'enumerate':
            continue
        if "id" not in var.varname:
            continue

        temp_dict = {}
        for v in var.possible_values:
            temp_dict[v] = []
        for transition in fsm.transitions:
            for action in transition.actions:
                if var.varname in action.action_label:
                    enum_assigned = action.action_label.split('=')[1].strip()
                    temp_dict[enum_assigned].append(transition.transition_label)
        ctr = 0
        outputFile.write('\t{0} = \n'.format(var.varname))
        for key in temp_dict.keys():
            if ctr == 0:
                outputFile.write('\t\tif (\n')
            else:
                outputFile.write('\t\telse if (\n')
            ctr += 1
            transitions = temp_dict[key]
            transitions = [fsm.fsm_label + '_transition = ' + transition for transition in transitions]
            outputFile.write('\t\t\t' + " or ".join(transitions) + '\n\t\t\t)\n')
            outputFile.write('\t\t\tthen ' + key + '\n')
        outputFile.write('\t\telse {0} -> pre {1};\n\n'.format(var.initial_value, var.varname))
    # Updates sequence numbers
    for seq_num in sequence_nums:
        reset_transitions = []
        increase_transitions = []
        seq_num_name = seq_num.seqname

        if seq_num_name == 'amf_ue_shared_seq':
            continue

        for transition in fsm.transitions:
            seq_changes = False
            for action in transition.actions:
                if seq_num_name in action.action_label:
                    action_label = action.action_label
                    action_label = action_label.replace(' ','')
                    # action_label = action_label.replace('+1)mod32)','+1))')
                    if '=0' in action_label:
                        reset_transitions.append(transition.transition_label)
                    else:
                        increase_transitions.append(transition.transition_label)

        outputFile.write('\n\t{0} = \n'.format(seq_num_name))
        outputFile.write('\t\tif (\n')
        reset_transitions = [fsm.fsm_label + '_transition = ' + r_transition for r_transition in reset_transitions]
        if not reset_transitions:
            outputFile.write('\t\t\tfalse\n\t\t\t)\n')
        else:
            outputFile.write('\t\t\t' + ' or '.join(reset_transitions) + '\n\t\t\t)\n')
        outputFile.write('\t\t\tthen ' + seq_num.start + '\n')
        outputFile.write('\t\telse if (\n')
        increase_transitions = [fsm.fsm_label + '_transition = ' + i_transition for i_transition in increase_transitions]
        if not increase_transitions:
            outputFile.write('\t\t\tfalse\n\t\t\t)\n')
        else:
            outputFile.write('\t\t\t' + ' or '.join(increase_transitions) + '\n\t\t\t)\n')
        outputFile.write('\t\t\tthen ({0} -> pre {1}) + 1\n'.format(seq_num.start, seq_num_name))

        outputFile.write('\t\telse {0} -> pre {1};\n'.format(seq_num.start, seq_num_name))

    if fsm.fsm_label == 'AMF_NAS':
        outputFile.write('\n\tamf_ue_shared_seq = amf_seq;\n')


    for var in fsm_state_vars:
        if var.datatype != 'bool':
            continue

        var_name = var.varname
        true_transitions = []
        false_transitions = []
        for transition in fsm.transitions:
            var_changed = False
            for action in transition.actions:
                if var_name in action.action_label:
                    action_label = action.action_label.replace(' ','')
                    if action_label.split(var_name)[1].lower().startswith('=false'):
                        false_transitions.append(transition.transition_label)
                    elif action_label.split(var_name)[1].lower().startswith('=true'):
                        true_transitions.append(transition.transition_label)
                    else:
                        print 'ERROR, Transition {0} does not assign a value for {1}'.format(transition.transition_label, var_name)

        outputFile.write('\n\t{0} = \n'.format(var_name))
        outputFile.write('\t\tif (\n')
        true_transitions = [fsm.fsm_label + '_transition = ' + t_transition for t_transition in true_transitions]
        if not true_transitions:
            outputFile.write('\t\t\tfalse\n\t\t\t)\n')
        else:
            outputFile.write('\t\t\t' + ' or '.join(true_transitions) + '\n\t\t\t)\n')
        outputFile.write('\t\t\tthen true\n')

        outputFile.write('\t\telse if (\n')
        false_transitions = [fsm.fsm_label + '_transition = ' + f_transition for f_transition in false_transitions]
        if not false_transitions:
            outputFile.write('\t\t\tfalse\n\t\t\t)\n')
        else:
            outputFile.write('\t\t\t' + ' or '.join(false_transitions) + '\n\t\t\t)\n')
        outputFile.write('\t\t\tthen false\n')
        outputFile.write('\t\telse {0} -> pre {1};\n'.format(var.initial_value, var_name))

    # Hard coding checks to avoid errors in nuXMV
    if fsm.fsm_label == 'AMF_NAS':
        outputFile.write('\tamf_auth_fail_count_check = amf_auth_fail_count < 3;\n')

    elif fsm.fsm_label == 'UE_NAS':
        outputFile.write('\trange = 8;\n')
        outputFile.write('\tue_auth_seq_check = ue_seq < amf_ue_shared_seq and amf_ue_shared_seq < (ue_seq + range);\n')
        outputFile.write('\treg_count_check = ue_reg_count < 5;\n')
        outputFile.write('\tue_auth_fail_count_check = ue_auth_fail_count < 3;\n')

    if fsm.fsm_label == 'UE_NAS':
        outputFile.write('--%MAIN;\n')

    if fsm.fsm_label == 'UE_RRC':
        outputFile.write('--%MAIN;\n')


    outputFile.write('tel\n')

def dump_adversarial_channel_nodes(outputFile, fsm, other_fsm_label):
    outputFile.write('\nnode {0}_to_{1}_adversarial_channel(\n'.format(fsm.fsm_label, other_fsm_label))
    outputFile.write('\tbenign_{0}_message : {0}_messages;\n'.format(fsm.fsm_label))
    outputFile.write('\tmalicious_{0}_message : {0}_messages;\n'.format(fsm.fsm_label))
    outputFile.write('\tnoisy : bool;\n')
    outputFile.write('\tmalicious : bool;\n')
    outputFile.write(')\n')

    outputFile.write('returns (\n')
    outputFile.write('\t{0}_message_to_{1} : {0}_messages;\n'.format(fsm.fsm_label, other_fsm_label))
    outputFile.write(')\n')

    outputFile.write('let\n')
    outputFile.write('\t{0}_message_to_{1} =\n'.format(fsm.fsm_label, other_fsm_label))
    outputFile.write('\tif ( noisy or malicious )\n')
    outputFile.write('\t\tthen malicious_{0}_message\n'.format(fsm.fsm_label))
    outputFile.write('\telse benign_{0}_message;\n'.format(fsm.fsm_label))
    outputFile.write('tel\n')

def dump_run_contract_node(outputFile, vars, fsms, sequence_nums, manual_checks):
    checks = [check.split(':=')[0].strip() for check in manual_checks if 'check' in check]
    outputFile.write('\ncontract Run_5G_FSM_contract(\n')
    ctr = 0

    # Outputs the environmental variables
    for fsm in fsms:
        fsm_label = fsm.fsm_label
        fsm_vars = [var for var in vars if var.fsm == fsm_label]
        fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']
        fsm_environment_vars = [var for var in fsm_vars if var.controltype == 'environment']

        if ctr == 0:
            outputFile.write('\n---- {0}_to_{1} adversarial channel variables ----\n'.format(fsm_label, fsms[1].fsm_label))
        else:
            outputFile.write('\n---- {0}_to_{1} adversarial channel variables ----\n'.format(fsm_label, fsms[0].fsm_label))
        # Malicious message to possibly inject
        outputFile.write('\tmalicious_{0}_message : {0}_messages;\n'.format(fsm_label))

        if ctr == 0:
            outputFile.write('\t{0}_to_{1}_noisy : bool;\n'.format(fsm_label, fsms[1].fsm_label))
            outputFile.write('\t{0}_to_{1}_malicious : bool;\n'.format(fsm_label, fsms[1].fsm_label))
        else:
            outputFile.write('\t{0}_to_{1}_noisy : bool;\n'.format(fsm_label, fsms[0].fsm_label))
            outputFile.write('\t{0}_to_{1}_malicious : bool;\n'.format(fsm_label, fsms[0].fsm_label))

        outputFile.write('\n---- {0} environment variables ----\n'.format(fsm_label))

        for var in fsm_environment_vars:
            if var.datatype == 'enumerate':
                outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
            else:
                outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

        ctr += 1
    outputFile.write(')\n')

    # Outputs the state variables
    outputFile.write('returns (\n')

    for fsm in fsms:
        fsm_label = fsm.fsm_label
        fsm_vars = [var for var in vars if var.fsm == fsm_label]
        fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']

        outputFile.write('---- {0} state and messages ----\n'.format(fsm_label))
        outputFile.write('\t{0}_state : {0}_states;\n'.format(fsm_label))
        outputFile.write('\t{0}_message : {0}_messages;\n'.format(fsm_label))



        outputFile.write('---- {0} STATE VARIABLES ----\n'.format(fsm_label))
        for var in fsm_state_vars:
            if var.datatype == 'enumerate':
                outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
            else:
                outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

        outputFile.write('---- {0} TRANSITION ----\n'.format(fsm_label))
        outputFile.write('\t{0}_transition : {0}_transitions;\n'.format(fsm_label))

    outputFile.write('---- SEQUENCE NUMBERS ----\n'.format(fsm_label))
    for seq_num in sequence_nums:
        outputFile.write('\t{0} : int;\n'.format(seq_num.seqname))

    outputFile.write('---- MANUAL CHECKS ----\n')
    for check in checks:
        outputFile.write('\t{0} : bool;\n'.format(check))

    outputFile.write('\t{0}_message_to_{1} : {0}_messages;\n'.format(fsms[0].fsm_label, fsms[1].fsm_label))
    outputFile.write('\t{0}_message_to_{1} : {0}_messages;\n'.format(fsms[1].fsm_label, fsms[0].fsm_label))

    outputFile.write(');\n')

    outputFile.write('let\n')
    outputFile.write('\tguarantee "g1" true;\n')

    outputFile.write('tel\n')

def dump_run_node(outputFile, vars, fsms, manual_checks, seq_num_0, seq_num_1, checks_1, checks_2):
    def dump_call_controller(fsm_to_invoke, seq_to_use, other_fsm, check_to_use, starting_state):
        checks = [check.split(':=')[0].strip() for check in check_to_use if 'check' in check]

        outputFile.write('\t({0}_state,\n'.format(fsm_to_invoke))
        outputFile.write('\t{0}_message,\n'.format(fsm_to_invoke))

        if fsm_to_invoke == 'AMF_NAS':
            outputFile.write('\t{0},\n'.format('amf_ue_shared_seq'))

        for seq in seq_to_use:
            if seq.seqname == 'amf_ue_shared_seq':
                continue
            outputFile.write('\t{0},\n'.format(seq.seqname))

        fsm_to_invoke_state_vars = [var for var in vars if var.controltype == 'state' and var.fsm == fsm_to_invoke]
        fsm_to_invoke_environment_vars = [var for var in vars if
                                  var.controltype == 'environment' and var.fsm == fsm_to_invoke]
        for var in fsm_to_invoke_state_vars:
            outputFile.write('\t{0},\n'.format(var.varname))

        # TODO: Checks
        for check in checks:
            outputFile.write('\t{0},\n'.format(check))

        outputFile.write('\t{0}_transition) =\n'.format(fsm_to_invoke))
        outputFile.write('\t{0}_controller (\n'.format(fsm_to_invoke))
        outputFile.write('\t\t{0}_message_to_{1},\n'.format(other_fsm, fsm_to_invoke))
        #outputFile.write('\t\t{0} -> pre {1}_state,\n'.format(starting_state, fsm_to_invoke))

        if fsm_to_invoke == 'UE_NAS':
            outputFile.write('\t\tamf_ue_shared_seq,\n')

        ctr = 0
        for var in fsm_to_invoke_environment_vars:
            if ctr == len(fsm_to_invoke_environment_vars) - 1:
                outputFile.write('\t\t{0}\n'.format(var.varname))
            else:
                outputFile.write('\t\t{0},\n'.format(var.varname))
            ctr += 1

        outputFile.write('\t);\n')

    def dump_call_adversarial(from_fsm, to_fsm):
        outputFile.write('\t{0}_message_to_{1} = \n'.format(from_fsm, to_fsm))
        outputFile.write('\t\t{0}_to_{1}_adversarial_channel(\n'.format(from_fsm, to_fsm))
        outputFile.write('\t\t\t{0}_null_action -> pre {0}_message,\n'.format(from_fsm))
        outputFile.write('\t\t\tmalicious_{0}_message,\n'.format(from_fsm))
        outputFile.write('\t\t\t{0}_to_{1}_noisy,\n'.format(from_fsm, to_fsm))
        outputFile.write('\t\t\t{0}_to_{1}_malicious\n'.format(from_fsm, to_fsm))
        outputFile.write('\t\t);\n')
    sequence_nums = create_seq_nums(seq_num_0, seq_num_1)

    checks = [check.split(':=')[0].strip() for check in manual_checks if 'check' in check]
    outputFile.write('\nnode Run_5G_FSM(\n')
    ctr = 0

    # Outputs the environmental variables
    for fsm in fsms:
        fsm_label = fsm.fsm_label
        fsm_vars = [var for var in vars if var.fsm == fsm_label]
        fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']
        fsm_environment_vars = [var for var in fsm_vars if var.controltype == 'environment']

        if ctr == 0:
            outputFile.write('\n---- {0}_to_{1} adversarial channel variables ----\n'.format(fsm_label, fsms[1].fsm_label))
        else:
            outputFile.write('\n---- {0}_to_{1} adversarial channel variables ----\n'.format(fsm_label, fsms[0].fsm_label))
        # Malicious message to possibly inject
        outputFile.write('\tmalicious_{0}_message : {0}_messages;\n'.format(fsm_label))

        if ctr == 0:
            outputFile.write('\t{0}_to_{1}_noisy : bool;\n'.format(fsm_label, fsms[1].fsm_label))
            outputFile.write('\t{0}_to_{1}_malicious : bool;\n'.format(fsm_label, fsms[1].fsm_label))
        else:
            outputFile.write('\t{0}_to_{1}_noisy : bool;\n'.format(fsm_label, fsms[0].fsm_label))
            outputFile.write('\t{0}_to_{1}_malicious : bool;\n'.format(fsm_label, fsms[0].fsm_label))

        outputFile.write('\n---- {0} environment variables ----\n'.format(fsm_label))

        for var in fsm_environment_vars:
            if var.datatype == 'enumerate':
                outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
            else:
                outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

        ctr += 1
    outputFile.write(')\n')

    # Outputs the state variables
    outputFile.write('returns (\n')

    for fsm in fsms:
        fsm_label = fsm.fsm_label
        fsm_vars = [var for var in vars if var.fsm == fsm_label]
        fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']

        outputFile.write('---- {0} state and messages ----\n'.format(fsm_label))
        outputFile.write('\t{0}_state : {0}_states;\n'.format(fsm_label))
        outputFile.write('\t{0}_message : {0}_messages;\n'.format(fsm_label))



        outputFile.write('---- {0} STATE VARIABLES ----\n'.format(fsm_label))
        for var in fsm_state_vars:
            if var.datatype == 'enumerate':
                outputFile.write('\t{0} : {0}_enum;\n'.format(var.varname))
            else:
                outputFile.write('\t{0} : {1};\n'.format(var.varname, var.datatype))

        outputFile.write('---- {0} TRANSITION ----\n'.format(fsm_label))
        outputFile.write('\t{0}_transition : {0}_transitions;\n'.format(fsm_label))

    outputFile.write('---- SEQUENCE NUMBERS ----\n'.format(fsm_label))
    for seq_num in sequence_nums:
        outputFile.write('\t{0} : int;\n'.format(seq_num.seqname))

    outputFile.write('---- MANUAL CHECKS ----\n')
    for check in checks:
        outputFile.write('\t{0} : bool;\n'.format(check))

    outputFile.write('\t{0}_message_to_{1} : {0}_messages;\n'.format(fsms[0].fsm_label, fsms[1].fsm_label))
    outputFile.write('\t{0}_message_to_{1} : {0}_messages;\n'.format(fsms[1].fsm_label, fsms[0].fsm_label))

    outputFile.write(');\n')

    # Write the signature down
    outputFile.write('(*@contract import \n')
    outputFile.write('Run_5G_FSM_contract(\n')

    ctr = 0
    for fsm in fsms:
        fsm_label = fsm.fsm_label
        fsm_vars = [var for var in vars if var.fsm == fsm_label]
        fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']
        fsm_environment_vars = [var for var in fsm_vars if var.controltype == 'environment']

        if ctr == 0:
            outputFile.write('\n---- {0}_to_{1} adversarial channel variables ----\n'.format(fsm_label, fsms[1].fsm_label))
        else:
            outputFile.write('\n---- {0}_to_{1} adversarial channel variables ----\n'.format(fsm_label, fsms[0].fsm_label))
        # Malicious message to possibly inject
        outputFile.write('\tmalicious_{0}_message,\n'.format(fsm_label))

        if ctr == 0:
            outputFile.write('\t{0}_to_{1}_noisy,\n'.format(fsm_label, fsms[1].fsm_label))
            outputFile.write('\t{0}_to_{1}_malicious,\n'.format(fsm_label, fsms[1].fsm_label))
        else:
            outputFile.write('\t{0}_to_{1}_noisy,\n'.format(fsm_label, fsms[0].fsm_label))
            outputFile.write('\t{0}_to_{1}_malicious,\n'.format(fsm_label, fsms[0].fsm_label))

        outputFile.write('\n---- {0} environment variables ----\n'.format(fsm_label))

        var_ctr = 0
        for var in fsm_environment_vars:
            if var_ctr == len(fsm_environment_vars) - 1 and ctr == 1:
                outputFile.write('\t{0}\n'.format(var.varname))
            else:
                outputFile.write('\t{0},\n'.format(var.varname))

            var_ctr += 1

        ctr += 1
    outputFile.write(')\n')

    # Outputs the state variables
    outputFile.write('returns (\n')

    for fsm in fsms:
        fsm_label = fsm.fsm_label
        fsm_vars = [var for var in vars if var.fsm == fsm_label]
        fsm_state_vars = [var for var in fsm_vars if var.controltype == 'state']

        outputFile.write('---- {0} state and messages ----\n'.format(fsm_label))
        outputFile.write('\t{0}_state,\n'.format(fsm_label))
        outputFile.write('\t{0}_message,\n'.format(fsm_label))


        outputFile.write('---- {0} STATE VARIABLES ----\n'.format(fsm_label))
        for var in fsm_state_vars:
            if var.datatype == 'enumerate':
                outputFile.write('\t{0},\n'.format(var.varname))
            else:
                outputFile.write('\t{0},\n'.format(var.varname))

        outputFile.write('---- {0} TRANSITION ----\n'.format(fsm_label))
        outputFile.write('\t{0}_transition,\n'.format(fsm_label))

    outputFile.write('---- SEQUENCE NUMBERS ----\n'.format(fsm_label))
    for seq_num in sequence_nums:
        outputFile.write('\t{0},\n'.format(seq_num.seqname))

    outputFile.write('---- MANUAL CHECKS ----\n')

    for check in checks:
        outputFile.write('\t{0},\n'.format(check))

    outputFile.write('\t{0}_message_to_{1},\n'.format(fsms[0].fsm_label, fsms[1].fsm_label))
    outputFile.write('\t{0}_message_to_{1}\n'.format(fsms[1].fsm_label, fsms[0].fsm_label))

    outputFile.write(');\n')
    outputFile.write('*)\n')

    outputFile.write('let\n')

    outputFile.write('---- Check Adversarial channel to see what message should be sent to UE----\n')
    dump_call_adversarial(fsms[1].fsm_label, fsms[0].fsm_label)


    outputFile.write('---- Update state variables for UE ----\n')
    dump_call_controller(fsms[0].fsm_label, seq_num_0, fsms[1].fsm_label, checks_1, fsms[0].init_state)

    outputFile.write('---- Check Adversarial channel to see what message should be sent to Network----\n')
    dump_call_adversarial(fsms[0].fsm_label, fsms[1].fsm_label)

    outputFile.write('---- Update state variables for Network ----\n')
    dump_call_controller(fsms[1].fsm_label, seq_num_1, fsms[0].fsm_label, checks_2, fsms[1].init_state)

    outputFile.write('tel\n')
    None

def main(client_in, server_in, outputFile):

    if 'ue' in client_in.lower():
        if 'rrc' in client_in.lower():
            client_fsm_label = 'UE_RRC'

        elif 'nas' in client_in.lower():
            client_fsm_label = 'UE_NAS'
    if 'bs' in server_in.lower():
        server_fsm_label = 'BS_RRC'
    if 'amf' in server_in.lower():
        server_fsm_label = 'AMF_NAS'

    parsing_result_client = parseDOT(client_in, client_fsm_label) # return (env_vars, state_vars, seq_vars, smv_vars, smv_seq_nums, fsm, smv_manual_checks)
    parsing_result_server = parseDOT(server_in, server_fsm_label) # return (env_vars, state_vars, seq_vars, smv_vars, smv_seq_nums, fsm, smv_manual_checks)


    vars = create_vars(parsing_result_client[3], parsing_result_server[3]) # seq_vars
    seq_nums = create_seq_nums(parsing_result_client[4], parsing_result_server[4]) # smv_vars
    fsms = create_fsms(parsing_result_client[5], parsing_result_server[5])

    channels, injective_adversaries = create_channels(client_fsm_label, server_fsm_label)
    manual_checks = compile_manual_checks(parsing_result_client[6], parsing_result_server[6])

    f = open(args.outputFile, "w")

    dump_states(f, fsms)
    dump_enumerate_variables(f, vars)
    dump_transition_enum(f, fsms)
    dump_messages(f, fsms)

    dump_helper_nodes(f)
    dump_controller_contract(f, fsms[0], fsms[1].fsm_label, vars, parsing_result_client[6], parsing_result_client[4])
    dump_controller_contract(f, fsms[1], fsms[0].fsm_label, vars, parsing_result_server[6], parsing_result_server[4])

    dump_transition_node(f, fsms[0], fsms[1].fsm_label, vars, parsing_result_client[6])
    dump_transition_node(f, fsms[1], fsms[0].fsm_label, vars, parsing_result_server[6])

    dump_controller_node(f, fsms[0], fsms[1].fsm_label, vars, parsing_result_client[6], parsing_result_client[4])
    dump_controller_node(f, fsms[1], fsms[0].fsm_label, vars, parsing_result_server[6], parsing_result_server[4])

    dump_adversarial_channel_nodes(f, fsms[0], fsms[1].fsm_label)
    dump_adversarial_channel_nodes(f, fsms[1], fsms[0].fsm_label)


    # TODO: Dump run contract
    dump_run_contract_node(f, vars, fsms, seq_nums, manual_checks)
    dump_run_node(f, vars, fsms, manual_checks, parsing_result_client[4], parsing_result_server[4], parsing_result_client[6], parsing_result_server[6])
    # TODO: Dump run node

    f.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""DOT to Lustre translator.""")

    parser.add_argument('-client', dest='client_dot_file', default="FSM/RRC/UE-RRC-5G.dot",
                        help="UE RRC dot file to read")
    parser.add_argument('-server', dest='server_dot_file', default="FSM/RRC/BS-RRC-5G.dot",
                        help="gNB RRC dot file to read")
    parser.add_argument('-o', dest='outputFile', default="5G-RRC.lus", help="smv file to write")

    # parser.add_argument('-client', dest='client_dot_file', default="FSM/NAS/UE-NAS-5G.dot", help="UE NAS dot file to read")
    # parser.add_argument('-server', dest='server_dot_file', default="FSM/NAS/AMF-NAS-5G.dot",
    #                     help="AMF NAS dot file to read")
    # parser.add_argument('-o', dest='outputFile', default="5G-NAS.smv", help="smv file to write")

    args = parser.parse_args()
    main(args.client_dot_file, args.server_dot_file, args.outputFile)

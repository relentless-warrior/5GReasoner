
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

    def set_datatype(self, datatype='boolean'):
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
                env_var = s.strip()
                env_vars.append(env_var)
                new_var = Variable(env_var, 'boolean', 'environment', None, None, fsm_label)
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
                        init_value = 'TRUE'
                    elif 'false' in init_value.lower():
                        init_value = 'FALSE'
                    #print 'init value = ', init_value
                    new_var = Variable(state_var_label, 'boolean', 'state', init_value, possible_values, fsm_label)
                else:
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
            #print 'checks = ', checks
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
                            action_label = action_label.replace('true', 'TRUE')
                        elif 'false' in value:
                            action_label = action_label.replace('false', 'FALSE')
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
                if "uesecctxupdated" in token:
                    print "hi"
                token = token.strip()
                if '(' in token:
                    token = token.split('(')[1]
                if ')' in token:
                    token = token.split(')')[0]

                if token in in_msgs:
                    if 'ue' in fsm_label.lower() and 'rrc' in fsm_label.lower():
                        msg_prefix = 'chan_BU=chanBU_'
                    elif 'ue' in fsm_label.lower() and 'nas' in fsm_label.lower():
                        msg_prefix = 'chan_AU = chanAU_'
                    elif 'bs' in fsm_label.lower() and 'rrc' in fsm_label.lower():
                        msg_prefix = 'chan_UB=chanUB_'
                    elif 'amf' in fsm_label.lower() and 'nas' in fsm_label.lower():
                        msg_prefix = 'chan_UA=chanUA_'

                    msg = msg_prefix + token
                    condition = condition.replace(token, msg)
                condition = condition.replace('true', 'TRUE')
                condition = condition.replace('false', 'FALSE')
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

def find_contendition_transitions(fsm):
    transition_contendingTransition_map = []
    for i in range(len(fsm.transitions)):
        transition = fsm.transitions[i]
        contendingTransitions = []
        for j in range(len(fsm.transitions)):
            if (i==j):
                continue
            if(fsm.transitions[i].start == fsm.transitions[j].start):
                contendingTransitions.append(fsm.transitions[j].transition_label)
        transition_contendingTransition_map.append((transition, contendingTransitions))
    return transition_contendingTransition_map

# dump vars
def dump_variables(file, vars, injective_adversaries):
    file.write('\nVAR\n\n')
    file.write('\n------------------- Environment and State variables --------------------\n')
    for var in vars:
        if var.varname == "uesecctxupdated":
            print "hi"
        if(var.datatype == 'boolean'):
            file.write(var.varname +  '\t:\t' + var.datatype + ';\t\n')
        elif (var.datatype == 'enumerate'):
            file.write(var.varname + '\t:\t{')
            for i in range(len(var.possible_values)):
                if(i == len(var.possible_values) -1 ):
                    file.write(var.possible_values[i])
                else:
                    file.write(var.possible_values[i] + ', ')
            file.write('};\t\n')

    for injective_adversary in injective_adversaries:
        file.write('attacker_inject_message_' + injective_adversary.active_channel_label.replace('_','') + '\t:\t' + 'boolean\t;\n')
    return

# dump sequence numbers
def dump_sequence_numbers(file, seq_nums):
    file.write('\n----------------- Sequence numbers -------------------\n')

    for seq_num in seq_nums:
        file.write(seq_num.seqname +  '\t:\t' + str(seq_num.start) + '..' + str(seq_num.end) + '\t;\n')
    return

# dumping states of a FSM
def dump_states(file, fsms):
    for fsm in fsms:
        file.write('\n---------------- state for ' + fsm.fsm_label + ' state machine ----------------\n')
        file.write('\n' + str(fsm.fsm_label).lower() + '_state\t:\n')
        file.write('{\n')
        for i in range(len(fsm.states)):
            if (i < len(fsm.states) - 1):
                file.write(str('\t' + fsm.states[i]) + ',\n')
            else:
                file.write('\t'+str(fsm.states[i]) + '\n')
        file.write('};\n')
    return

# get the unique action_names of a fsm
def get_unique_action_names(fsm):
    action_labels = []
    for transition in fsm.transitions:
        for action in transition.actions:
            if (action.action_label not in action_labels and action.channel.channel_label.lower() != 'internal'):
                action_labels.append(action.action_label)
    return action_labels


# dump fsm_actions
def dump_actions(file, fsms):
    for fsm in fsms:
        file.write('------------ Possible ' + fsm.fsm_label + ' actions ----------------\n')
        action_labels = get_unique_action_names(fsm)
        fsm_label_entity= fsm.fsm_label.lower().split('_')[0].strip()
        #print fsm_label_entity
        file.write('\n'+ fsm.fsm_label.lower() + '_action\t:\n')
        #file.write('\n' + fsm_label_entity + '_action\t:\n')
        file.write('{\n')
        for i in range(len(action_labels)):
            if (i < len(action_labels) - 1):
                #file.write('\t'+fsm.fsm_label.lower() + '_' + action_labels[i] + ',\n')
                file.write('\t' + action_labels[i] + ',\n')
            else:
                #file.write('\t'+fsm.fsm_label.lower() + '_' + action_labels[i] + '\n')
                file.write('\t' + action_labels[i] + '\n')

        if(len(action_labels) == 0):
            #file.write('\t' + fsm.fsm_label.lower() + '_null_action\n')
            file.write('\t' + fsm.fsm_label_entity + '_null_action\n')
        file.write('};\n')
    return

# get the actions of a specific channel
def get_channel_actions(channel_start, channel_end, fsms):
    action_labels = []

    for fsm in fsms:

        if channel_start in fsm.fsm_label:
            for transition in fsm.transitions:
                for action in transition.actions:

                    if (action.channel.start.lower() == channel_start.lower() and action.channel.end.lower() == channel_end.lower() and
                    action.channel.channel_label != 'internal'):
                        if(action.action_label not in action_labels):
                            action_labels.append(action.action_label)
    #print action_labels
    return action_labels


# mapping (channel, actions)
def get_channel_actions_map(channels, fsms):
    channel_actions_map=[]
    for i in range(len(channels)):
        channel_actions_map.append((channels[i], get_channel_actions(channels[i].start, channels[i].end, fsms)))
    return channel_actions_map


def dump_adversary_channel(file, channels, fsms):
    #print (channels)
    for channel in channels:
        file.write('\n--------------- Adversarial channel from ' + channel.start.upper() + ' to ' + channel.end.upper() +' ---------------\n')
        actions = get_channel_actions(channel.start, channel.end, fsms)

        file.write('\n' + channel.channel_label + '\t:\n')
        file.write('{\n')
        for i in range(len(actions)):
            if (i < len(actions) - 1):
                file.write('\t'+channel.channel_label.replace('_', '') + '_'+ str(actions[i]).strip() + ',\n')
            else:
                file.write('\t' + channel.channel_label.replace('_', '') + '_'+ str(actions[i]).strip() + '\n')
        file.write('};\n')


# dump Injection Adversary Action for each of the channels
def dump_injective_adversary(file, channels, injective_adversaries, fsms):
    for injective_adversary in injective_adversaries:
        active_channel_label = injective_adversary.active_channel_label
        # find if the active channel is one of the channels
        for channel in channels:
            if (active_channel_label.lower() == channel.channel_label.lower()):
                action_labels = get_channel_actions(channel.start, channel.end, fsms)
                inj_adv_act_ch_name = injective_adversary.inj_adv_label
                file.write(
                    '\n--------------- Injective adversary action for channel '+ channel.channel_label + ' ---------------\n')
                inj_adv_act_ch_name = inj_adv_act_ch_name[0:inj_adv_act_ch_name.rfind('_')] + '_act_' + inj_adv_act_ch_name[inj_adv_act_ch_name.rfind('_') + 1:]
                file.write('\n' + inj_adv_act_ch_name + '\t:\n')
                file.write('{\n')
                for i in range(len(action_labels)):
                    prefix = injective_adversary.inj_adv_label[injective_adversary.inj_adv_label.rfind('_')+1:]
                    if (i < len(action_labels) - 1):

                        file.write('\tadv_' + prefix + '_' + action_labels[i] + ',\n')
                    else:
                        file.write('\tadv_' + prefix +'_' + action_labels[i] + '\n')
                file.write('};\n')
    return


# dump transitions of the FSMs
def dump_transitions(file, fsms):
    # dumping actions
    for fsm in fsms:
        file.write('\n-----------------' + fsm.fsm_label +' transitions --------------------\n')
        transition_contendingTransitions_map = find_contendition_transitions(fsm)
        for i in range(len(fsm.transitions)):
            condition = fsm.transitions[i].condition
            file.write(fsm.transitions[i].transition_label +'\t:=\t (' + fsm.fsm_label.lower()+ '_state = ' +
                       fsm.transitions[i].start + ' & '+ condition + ')\t;\n')
    return

# dump the controls for noisy channels
def dump_noisy_channel_controls(file, channels):
    file.write('\n------------------- Noisy Channels --------------------\n')
    for channel in channels:
        prefix = channel.channel_label[channel.channel_label.rfind('_') + 1:]
        if(channel.noisy.lower() == 'yes' or channel.noisy.lower() == 'true'):
            file.write('noisy_channel_' + prefix.strip() + ':=\tTRUE;\n')
        elif (channel.noisy.lower() == 'no' or channel.noisy.lower() == 'false' ):
            file.write('noisy_channel_' + prefix.strip() + ':=\tFALSE;\n')
    return

#dump the controls for adversarial channels
def dump_adversarial_channel_controls(file, injective_adversaries):
    file.write('\n------------------- Adversary enabled or not --------------------\n')
    for injective_adversary in injective_adversaries:
        prefix = injective_adversary.inj_adv_label + '_enabled'
        #if(injective_adversary.alwayson.lower() == 'yes' or injective_adversary.alwayson.lower() == 'true'):
        file.write(prefix.strip() + ':=\tTRUE;\n')
        #elif(injective_adversary.alwayson.lower() == 'no' or injective_adversary.alwayson.lower() == 'false'):
        #    file.write(prefix.strip() + ':=\tFALSE;\n')
    return



def dump_manual(input_file, file, section_name):
    # create element tree object
    tree = ET.parse(input_file)

    # get root element
    root = tree.getroot()

    manual_dumps = root.find('manual_dump')
    if (root.find('manual_dump')):
        for instance in manual_dumps:
            section = instance.find('section').text
            section = str(section).strip().upper()
            if (section in str(section_name).upper()):
                text = instance.find('text').text
                lines = str(text).split('\n')
                for line in lines:
                    file.write(line.lstrip() + '\n')
    return

def dump_manual_checks(file, manual_checks):
    for check in manual_checks:
        file.write(check + ';\n')
    return

def dump_defines(file, channels, injective_adversaries, fsms, manual_checks):
    file.write('\n\nDEFINE\n')
    dump_transitions(file, fsms)
    # dump_noisy_channel_controls(file, channels)
    dump_adversarial_channel_controls(file, injective_adversaries)
    dump_manual_checks(file, manual_checks)
    return


# dump adversarial state machines
def dump_adversarial_state_machines(file, injective_adversaries, channel_actions_map):
    file.write('\n------------------- Adversarial state machines --------------------\n')
    for injective_adversary in injective_adversaries:
        inj_adv_act_chanLabel = injective_adversary.inj_adv_label[:injective_adversary.inj_adv_label.rfind('_')] + '_act_' + injective_adversary.inj_adv_label[injective_adversary.inj_adv_label.rfind('_') + 1 :]
        file.write('\ninit(' + inj_adv_act_chanLabel + ')\t:=\n')
        file.write('{\n')
        for i in range(len(channel_actions_map)):
            if(channel_actions_map[i][0].channel_label.lower() == injective_adversary.active_channel_label.lower()):
                action_labels = channel_actions_map[i][1]
                for i in range(len(action_labels)):
                    prefix = injective_adversary.inj_adv_label[injective_adversary.inj_adv_label.rfind('_')+1:]
                    if (i < len(action_labels) - 1):
                        file.write('\tadv_' + prefix + '_' + action_labels[i] + ',\n')
                    else:
                        file.write('\tadv_' + prefix +'_' + action_labels[i] + '\n')
                file.write('};\n')
        file.write('\nnext(' + inj_adv_act_chanLabel + ')\t:=\tcase\n')
        file.write('TRUE\t:\t{\n')
        for i in range(len(channel_actions_map)):
            if (channel_actions_map[i][0].channel_label.lower() == injective_adversary.active_channel_label.lower()):
                action_labels = channel_actions_map[i][1]
                for i in range(len(action_labels)):
                    prefix = injective_adversary.inj_adv_label[injective_adversary.inj_adv_label.rfind('_') + 1:]
                    if (i < len(action_labels) - 1):
                        file.write('\tadv_' + prefix + '_' + action_labels[i] + ',\n')
                    else:
                        file.write('\tadv_' + prefix + '_' + action_labels[i] + '\n')
                file.write('};\n')
                file.write('esac\t;\n')

    return

# get the mapping (fsm, (deststate, transitions))
# for each deststate of a FSM, find the transitions
# transitions are list of transition_labels
def get_fsm_deststate_transition_map(fsms):
    fsm_deststate_transition_map = []
    for fsm in fsms:
        deststate_transition_map = []
        for state in fsm.states:
            transitions = []
            for transition in fsm.transitions:
                if (str(state).lower().strip() == str(transition.end).lower().strip()):
                    transitions.append(transition.transition_label)
            deststate_transition_map.append((state, transitions))
        fsm_deststate_transition_map.append((fsm, deststate_transition_map))

    return fsm_deststate_transition_map


# dump FSM transition state machines
def dump_state_machines(file, fsms):
    fsm_deststate_transition_map = get_fsm_deststate_transition_map(fsms)
    for i in range(len(fsm_deststate_transition_map)):
        fsm = fsm_deststate_transition_map[i][0]
        file.write('\n\n---------------' + fsm.fsm_label + ' state machine ------------------\n')
        file.write("\ninit(" + fsm.fsm_label.lower() +'_state)\t:=' +
                   fsm.init_state.lower() + ';\n')
        file.write("\nnext(" + fsm.fsm_label.lower() + '_state)\t:=\t case\n\n')
        deststate_transition_map = fsm_deststate_transition_map[i][1]
        for j in range(len(deststate_transition_map)):
            deststate = deststate_transition_map[j][0]
            transition_labels = deststate_transition_map[j][1]
            if (len(transition_labels) != 0):
                file.write('(')
            for k in range(len(transition_labels)):
                if(k < len(transition_labels)-1):
                    file.write(transition_labels[k] + ' | ')
                else:
                    file.write(transition_labels[k])
            if(len(transition_labels) != 0):
                file.write(' )\t:\t' + deststate.lower() +'\t;\n')
        file.write('TRUE\t:\t' + fsm_deststate_transition_map[i][0].fsm_label.lower() +'_state\t;\n')
        file.write('esac\t;')

    return


# get the mapping (fsm, (action, transitions))
# for each action of a FSM, find the corresponding transitions
def get_fsm_action_transition_map(fsms):
    fsm_action_transition_map = []
    for fsm in fsms:
        action_transition_map = []
        action_labels = get_unique_action_names(fsm)
        for action_label in action_labels:
            transitions = []
            for transition in fsm.transitions:
                for action in transition.actions:
                    if (action_label.lower() == action.action_label.lower()):
                        transitions.append(transition.transition_label)
            action_transition_map.append((action_label, transitions))
        fsm_action_transition_map.append((fsm, action_transition_map))
    return fsm_action_transition_map


def dump_action_state_machines(file, fsms):
    fsm_action_transition_map = get_fsm_action_transition_map(fsms)
    for i in range(len(fsm_action_transition_map)):
        # file.write("\n\n\ninit(" + fsm_action_transition_map[i][0].fsm_label.lower() +'_action)\t:= ' +
        #            fsm_action_transition_map[i][0].fsm_label.lower() + '_null_action\t;\n')
        file.write("\n\n\ninit(" + fsm_action_transition_map[i][0].fsm_label.lower() + '_action)\t:= null_action\t;\n')
        file.write("\nnext(" + fsm_action_transition_map[i][0].fsm_label.lower() + '_action)\t:=\t case\n\n')
        action_transition_map = fsm_action_transition_map[i][1]
        for j in range(len(action_transition_map)):
            file.write('(')
            action_label = action_transition_map[j][0]
            #print action_label
            transition_labels = action_transition_map[j][1]
            for k in range(len(transition_labels)):
                if(k < len(transition_labels)-1):
                    file.write(transition_labels[k] + ' | ')
                else:
                    file.write(transition_labels[k])
            fsm_label_entity = fsm_action_transition_map[i][0].fsm_label.lower().split('_')[0].strip()
            #file.write(' )\t:\t' + fsm_action_transition_map[i][0].fsm_label.lower() + '_'+ action_label +'\t;\n')
            file.write(' )\t:\t' + action_label + '\t;\n')

        #file.write('TRUE\t:\t' + fsm_action_transition_map[i][0].fsm_label.lower() +'_null_action\t;\n')
        file.write('TRUE\t:\t null_action\t;\n')
        file.write('esac\t;')

    return


def dump_adv_channel_state_machines(file, channels, injective_adversaries, fsms):
    for injective_adversary in injective_adversaries:
        file.write('\n\ninit(' + injective_adversary.active_channel_label + ')\t:=\t' +
                   injective_adversary.active_channel_label.replace('_','') + '_null_action;\n')
        file.write('\nnext(' + injective_adversary.active_channel_label + ')\t:=\t case\n')
        attacher_inject_msg = 'attacker_inject_message_' + injective_adversary.active_channel_label.replace('_','')
        inj_adv_chan_enabled = 'inj_adv_' + injective_adversary.inj_adv_label[injective_adversary.inj_adv_label.rfind('_') + 1 : ] + '_enabled'
        inj_adv_act_chan = 'inj_adv_act_' + injective_adversary.inj_adv_label[injective_adversary.inj_adv_label.rfind('_') + 1 : ]
        for channel in channels:
            if (channel.channel_label.lower() == injective_adversary.active_channel_label.lower()):
                action_labels = get_channel_actions(channel.start, channel.end, fsms)
                for action_label in action_labels:
                    adv_chan_act = 'adv_' + injective_adversary.inj_adv_label[injective_adversary.inj_adv_label.rfind('_')+1:] + '_' + action_label
                    file.write(attacher_inject_msg + '\t&\t' + inj_adv_chan_enabled + '\t&\t'+ inj_adv_act_chan + '\t=\t')
                    file.write(adv_chan_act + '\t:\t' + injective_adversary.active_channel_label.replace('_', '') +'_' + action_label + '\t;\n')


                #noisy_channel_chan = 'noisy_channel_' + channel.channel_label[channel.channel_label.rfind('_') + 1 : ]
                entity_action = channel.start.lower() + '_action'
                for action_label in action_labels:
                    entity_action_value = channel.start.lower() + '_' + action_label
                    entity_action_value = action_label
                    chan_value = channel.channel_label.replace('_', '') + '_' + action_label
                    #file.write('! ' + noisy_channel_chan + '\t&\t'+ entity_action + '\t=\t '+ entity_action_value + '\t:\t' + chan_value +'\t;\n')
                    file.write(entity_action + '\t=\t ' + entity_action_value + '\t:\t' + chan_value + '\t;\n')
                #
                # file.write('\nTRUE\t:\n')
                # file.write('{\n')
                # for i in range(len(action_labels)):
                #     chan_value = channel.channel_label.replace('_', '') + '_' + action_labels[i]
                #     if(i < len(action_labels)-1):
                #         file.write('\t'+chan_value + ',\n')
                #     else:
                #         file.write('\t' + chan_value + '\n')

                file.write('TRUE\t: {')
                chan_value = channel.channel_label.replace('_', '') + '_null_action'
                file.write(chan_value + '}\t;\n')
                file.write('esac\t;\n')
    return


def dump_state_variable_state_machines(file, vars, fsms):
    var_value_transition_map = []
    file.write('\n\n--------------- State Variables state machine ------------------\n')
    for var in vars:
        if (var.controltype.strip() in 'state'):
            state_variable = var.varname
            #print var.varname
            value_transition_map = []
            for possible_value in var.possible_values:
                transitions = []
                for fsm in fsms:
                    for transition in fsm.transitions:
                        for action in transition.actions:
                            if (action.channel.channel_label.lower() == 'internal'):
                                state_variable = action.action_label.split('=')[0]
                                #print state_variable
                                if(state_variable.strip() in var.varname):
                                    value = action.action_label.split('=')[1]
                                    # print 'dump_state_variable_state_machines: action_label = ', action.action_label
                                    # print 'value = ', value
                                    # print 'possible_values = ', var.possible_values
                                    if(possible_value == value.strip()):
                                        #print (state_variable, var.initial_value, value, transition.transition_label)
                                        transitions.append(transition)
                if (len(transitions)>0):
                    value_transition_map.append((possible_value, transitions))

            if(len(value_transition_map) > 0):
                var_value_transition_map.append((var, value_transition_map))

    print ("--------- dump --------")
    for i in range(len(var_value_transition_map)):
        var = var_value_transition_map[i][0]
        state_variable = var.varname
        value_transition_map = var_value_transition_map[i][1]

        if(var.datatype == 'boolean'):
            file.write("\n\n\ninit(" + state_variable + ')\t:= ' + var.initial_value.upper() + '\t;\n') # TRUE and FALSE in uppercase
        elif(var.datatype == 'enumerate'):
            file.write("\n\n\ninit(" + state_variable + ')\t:= ' + var.initial_value + '\t;\n')

        file.write("\nnext(" + state_variable + ')\t:=\t case\n')
        for j in range(len(value_transition_map)):
            val = value_transition_map[j][0]
            transitions = value_transition_map[j][1]
            file.write('(')
            for k in range(len(transitions)):
                if(k == len(transitions)-1):
                    file.write(transitions[k].transition_label)
                else:
                    file.write(transitions[k].transition_label + ' | ')
            file.write(' )\t:\t' + val + '\t;\n')
        file.write('TRUE\t:\t' +  var.varname+ '\t;\n')
        file.write('esac\t;\n')

    return

def dump_seq_num_state_machines(file, seq_nums, fsms):
    seqnum_value_transition_map = []
    for seq_num in seq_nums:
        seqname = seq_num.seqname
        value_transition_map = []
        for possible_value in seq_num.possible_values:
            possible_value = possible_value.lstrip()
            #print 'possible_value = ', possible_value
            transitions = []
            for fsm in fsms:
                for transition in fsm.transitions:
                    for action in transition.actions:
                        if (action.channel.channel_label.lower() == 'internal'):
                            sname = str(action.action_label.split('=')[0]).strip()

                            if (seqname.strip() == sname):
                                #print 'sname = ', sname
                                next_value = str(action.action_label.split('=')[1]).strip()

                                if (possible_value == next_value.strip()):
                                    #print 'possible_value matched'
                                    transitions.append(transition)
            if (len(transitions) > 0):
                value_transition_map.append((possible_value, transitions))

        if (len(value_transition_map) > 0):
            seqnum_value_transition_map.append((seq_num, value_transition_map))


    print("--------- dump --------")
    file.write('\n\n')
    for i in range(len(seq_nums)):
        file.write('init(' + seq_nums[i].seqname + ')\t:= ' + seq_nums[i].start + '\t;\n')


    for i in range(len(seqnum_value_transition_map)):
        seqname = seqnum_value_transition_map[i][0].seqname
        value_transition_map = seqnum_value_transition_map[i][1]
        file.write('\nTRANS\n')
        file.write('case\n')
        for j in range(len(value_transition_map)):
            val = value_transition_map[j][0]
            transitions = value_transition_map[j][1]
            file.write('(')
            for k in range(len(transitions)):
                if (k == len(transitions) - 1):
                    file.write(transitions[k].transition_label)
                else:
                    file.write(transitions[k].transition_label + ' | ')
            file.write(' )\t:\tnext(' + seqname + ')\t=\t' +  val + '\t;\n')

        file.write('TRUE\t:\tnext(' + seqname + ')\t=\t' + seqname +'\t;\n')
        file.write('esac\t;\n')

    return

def dump_assigns(file, vars, seq_nums, fsms, channels, injective_adversaries):
    file.write('\n\nASSIGN\n\n')
    channel_actions_map = get_channel_actions_map(channels, fsms)
    dump_adversarial_state_machines(file, injective_adversaries, channel_actions_map)
    dump_state_machines(file, fsms)
    dump_action_state_machines(file, fsms)
    dump_adv_channel_state_machines(file, channels, injective_adversaries, fsms)
    dump_state_variable_state_machines(file, vars, fsms)
    dump_seq_num_state_machines(file, seq_nums, fsms)


    return


def draw_fsms(fsms):
    for fsm in fsms:
        fsm_digraph = 'digraph ' + fsm.fsm_label + '{\n'
        fsm_digraph += 'rankdir = LR;\n'
        fsm_digraph += 'size = \"8,5\"\n'
        for state in fsm.states:
            fsm_digraph += 'node [shape = circle, label=\"' + state + '\"]' + state + ';\n'

        for transition in fsm.transitions:
            fsm_digraph += transition.start + ' -> ' + transition.end + ' [label = \"' + transition.transition_label + ': '+ transition.condition + '/\n'
            for i in range(len(transition.actions)):
                if(i == len(transition.actions)-1):
                    fsm_digraph += transition.actions[i].action_label.lstrip()
                else:
                    fsm_digraph += transition.actions[i].action_label.lstrip() + ', '
            fsm_digraph += '\"]\n'
        fsm_digraph += '}\n'
        fsmOutPutFileName = fsm.fsm_label + '.dot'
        f = open(fsmOutPutFileName, "w")
        f.write(fsm_digraph)
        print (fsm_digraph)
        f.close()


    return


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
    print 'manual_checks = ', manual_checks
    f = open(args.outputFile, "w")
    f.write("MODULE main\n")
    dump_variables(f, vars, injective_adversaries)
    dump_sequence_numbers(f, seq_nums)
    dump_states(f, fsms)
    dump_actions(f, fsms)
    dump_adversary_channel(f, channels, fsms)
    dump_injective_adversary(f, channels, injective_adversaries, fsms)

    dump_defines(f, channels, injective_adversaries, fsms, manual_checks)
    dump_assigns(f, vars, seq_nums, fsms, channels, injective_adversaries)
    f.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""DOT to SMV translator.""")

    # parser.add_argument('-client', dest='client_dot_file', default="FSM/RRC/UE-RRC-5G.dot",
    #                     help="UE RRC dot file to read")
    # parser.add_argument('-server', dest='server_dot_file', default="FSM/RRC/BS-RRC-5G.dot",
    #                     help="gNB RRC dot file to read")
    # parser.add_argument('-o', dest='outputFile', default="5G-RRC.smv", help="smv file to write")

    parser.add_argument('-client', dest='client_dot_file', default="FSM/UE-NAS-5G.dot", help="UE NAS dot file to read")
    parser.add_argument('-server', dest='server_dot_file', default="FSM/AMF-NAS-5G.dot",
                        help="AMF NAS dot file to read")
    parser.add_argument('-o', dest='outputFile', default="5G-NAS.smv", help="smv file to write")

    args = parser.parse_args()
    main(args.client_dot_file, args.server_dot_file, args.outputFile)

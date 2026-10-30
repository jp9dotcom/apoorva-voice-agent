class AgentState:

    def __init__(self):

        self.last_tool = None
        self.last_tool_result = None
        self.last_tool_signature = None

        self.iteration = 0

        self.task_complete = False

    def reset(self):

        self.last_tool = None
        self.last_tool_result = None
        self.last_tool_signature = None

        self.iteration = 0

        self.task_complete = False

from enum import Enum
import json
from pathlib import Path
from typing import Iterable, List, Optional 
from pydantic import BaseModel, Field, model_validator 

from codingagent.packages.tools.tool import builtin_mcp

TASKS_FILE = Path("tasks.json")

class TaskState(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"

class Task(BaseModel):
    id: int = Field(..., description="Unique ID for this task")
    description: Optional[str] = Field(None, description="Detailed explanation of the task")
    state: TaskState = Field(..., description="Current status of the task")

class Operation(str, Enum):
    create = "create"
    update = "update"

class ManageTaskInput(BaseModel):
    operation: Operation = Field(..., description="The operation to perform on the task list")
    id: Optional[int] = Field(None, description="Task ID (required for update)")
    title: Optional[str] = Field(None, description="Title for the task (required for create)")
    description: Optional[str] = Field(None, description="Description for the task")
    state: Optional[TaskState] = Field(None, description="State for the task")

def load_tasks() -> List[Task]:
    if not TASKS_FILE.exists():
        return []
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Task(**t) for t in data]
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_tasks(tasks: List[Task]):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump([t.model_dump() for t in tasks], f, indent=2)

def _get_next_id(tasks: List[Task]) -> int:
    return max((t.id for t in tasks), default=0) + 1

def _enforce_single_in_progress(tasks: List[Task]):
    if any(t.state == TaskState.in_progress for t in tasks):
        raise ValueError("Only one task may be in_progress at a time.")

def _clear_if_all_completed(tasks: List[Task]) -> List[Task]:
    if tasks and all(t.state == TaskState.completed for t in tasks):
        return []  # Clear all tasks
    return tasks

@builtin_mcp
def todo_read(r: str = "") -> str:
    """
    Use this tool to read the current to-do list for the session. This tool should be used proactively and frequently to ensure that you are aware of
    the status of the current task list. You should make use of this tool as often as possible, especially in the following situations:
    - At the beginning of conversations to see what's pending
    - Before starting new tasks to prioritize work
    - When the user asks about previous tasks or plans
    - Whenever you're uncertain about what to do next
    - After completing tasks to update your understanding of remaining work
    - After every few messages to ensure you're on track

    Usage:
    - Returns a list of todo items with their status, priority, and content
    - Use this information to track progress and plan next steps
    - If no todos exist yet, an empty list will be returned
    """
    return json.dump([task.model_dump_json() for task in load_tasks()])

def todo_update(task_index: int, task_state: str) -> str:
    """
    Use this tool to update the state of a task in the current todo list. 
    
    Parameters:
    task_index (int): 0-based index of the task which state needs to be updated
    task_state (str): state to set task to (valid values: in_progress, complete)

    Usage:
    - Only update the state of one task at a time
    """
    tasks = load_tasks()
    if task_index < 0:
        raise ValueError("task_index is not a valid index into a list")
    
    if task_index >= len(tasks):
       raise ValueError("task_index is greater thanthe number of recorded tasks") 

    if task_state not in TaskState:
        raise ValueError(f"{task_state} is not a valid task state, valid states are 'pending', 'in_progress', 'completed'")
    
    state = TaskState.pending
    if task_state == TaskState.completed:
       state = TaskState.completed 
    elif task_state == TaskState.in_progress:
        state = TaskState.in_progress

    if state == TaskState.pending:
        raise ValueError(f"can not mark task {tasks[task_index]} as pending, it is already in pending")
    
    task = tasks[task_index]
    task.state = state
    tasks[task_index] = task

    if task_index == len(tasks)-1 and task.state == TaskState.completed:
        _clear_if_all_completed(tasks) 
        return json.dumps({"output": "all tasks completed"})

    if task.state == TaskState.completed:
        return json.dumps({"output": f"done with task at index {task_index}, next task is {tasks[task_index+1].description}"})

    return json.dumps({"output": f"updated task at index {task_index} to state {task_state}"})

@builtin_mcp
def todo_create(tasks: List[str]) -> str:
    """Create a todo list, to keep track of progress during complex tasks.

    Parameters:
    1. tasks: an array of strings, where each element is a task to execute with tasks as the key
    for ex. ["Initialise project", "create main.rs", "implement algorithm in main.rs"]

    When to use:
    1. Complex multi-step tasks - When a task requires 3 or more distinct steps or actions
    2. Non-trivial and complex tasks - Tasks that require careful planning or multiple operations
    3. User explicitly requests todo list - When the user directly asks you to use the todo list
    4. After receiving new instructions - Immediately capture user requirements as todos
    5. When you start working on a task - Mark it as in_progress BEFORE beginning work. Ideally you should only have one todo as in_progress at a time
    6. After completing a task - Mark it as completed and add any new follow-up tasks discovered during implementation

    When NOT to use:
    1. There is only a single, straightforward task
    2. The task is trivial and tracking it provides no organizational benefit
    3. The task can be completed in less than 3 trivial steps
    4. The task is purely conversational or informational

    NOTE that you should not use this tool if there is only one trivial task to do. In this case you are better off just doing the task directly.

    Usage:
    1. Task States: Use these states to track progress:
        - pending: Task not yet started
        - in_progress: Currently working on (limit to ONE task at a time)
        - completed: Task finished successfully
    2. Task Management:
        - Update task status in real-time as you work
        - Mark tasks complete IMMEDIATELY after finishing (don't batch completions)
        - Only have ONE task in_progress at any time
        - Complete current tasks before starting new ones
        - Remove tasks that are no longer relevant from the list entirely
    3. Task Completion Requirements:
        - ONLY mark a task as completed when you have FULLY accomplished it
        - If you encounter errors, blockers, or cannot finish, keep the task as in_progress
        - When blocked, create a new task describing what needs to be resolved
        - NEVER mark a task as completed if:
            - Tests are failing
            - Implementation is partial
            - You encountered unresolved errors
            - ou couldn't find necessary files or dependencies
    4. Task Breakdown
        - IMPORTANT: Create specific, actionable items
        - Break complex tasks into smaller, manageable steps
        - Use clear, descriptive task names
    When in doubt, use this tool. Being proactive with task management demonstrates attentiveness and ensures you complete all requirements successfully.
    """

    if not isinstance(tasks, Iterable):
        raise ValueError("tasks needs to be a list of tasks, but it is not")

    if len(load_tasks()) != 0:
        raise ValueError("old list of tasks still not done, complete old tasks before creating new ones, update them with todo_update tool")

    tasks = []
    for idx, task in enumerate(tasks):
        tasks.append(Task(id=idx, description=task, state=TaskState.pending))

    save_tasks(tasks)

    return json.dumps({"output": f"created todo list containing the following: {tasks}"})

    if data.operation == Operation.create:
        if data.state == TaskState.in_progress:
            _enforce_single_in_progress(tasks)
        new_task = Task(
            id=_get_next_id(tasks),
            title=data.title,
            description=data.description,
            state=data.state or TaskState.pending
        )
        tasks.append(new_task)
        save_tasks(tasks)
        return new_task.model_dump_json()

    elif data.operation == Operation.update:
        updated_task = None
        for t in tasks:
            if t.id == data.id:
                if data.state == TaskState.in_progress and t.state != TaskState.in_progress:
                    _enforce_single_in_progress(tasks)
                if data.title is not None:
                    t.title = data.title
                if data.description is not None:
                    t.description = data.description
                if data.state is not None:
                    t.state = data.state
                updated_task = t
                break
        if updated_task is None:
            raise ValueError(f"Task with ID {data.id} not found")

        # Auto-clear if last task completed
        tasks = _clear_if_all_completed(tasks)
        save_tasks(tasks)
        return updated_task.model_dump_json()

    else:
        raise ValueError(f"Unknown operation: {data.operation}")
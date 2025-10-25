use pyo3::prelude::*;
use pyo3::types::PyTuple;
use std::collections::{HashMap, VecDeque};
use std::sync::Mutex;
use once_cell::sync::Lazy;

type GuildId = u64;
type QueueItem = (String, u64); // (text, speaker_id)

static QUEUES: Lazy<Mutex<HashMap<GuildId, VecDeque<QueueItem>>>> = Lazy::new(|| Mutex::new(HashMap::new()));

#[pyfunction]
fn add_to_queue(guild_id: u64, text: String, speaker_id: u64) {
    let mut queues = QUEUES.lock().unwrap();
    let queue = queues.entry(guild_id).or_insert_with(VecDeque::new);
    queue.push_back((text, speaker_id));
}

#[pyfunction]
fn get_next(py: Python, guild_id: u64) -> PyResult<PyObject> {
    let mut queues = QUEUES.lock().unwrap();
    if let Some(queue) = queues.get_mut(&guild_id) {
        if let Some((text, speaker_id)) = queue.pop_front() {
            let tuple = PyTuple::new(py, &[text.into_py(py), speaker_id.into_py(py)])?;
            return Ok(tuple.into_py(py));
        }
    }
    Ok(py.None())
}

#[pyfunction]
fn clear_queue(guild_id: u64) {
    let mut queues = QUEUES.lock().unwrap();
    queues.remove(&guild_id);
}

#[pyfunction]
fn queue_length(guild_id: u64) -> usize {
    let queues = QUEUES.lock().unwrap();
    queues.get(&guild_id).map(|q| q.len()).unwrap_or(0)
}

#[pymodule]
fn rust_queue(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(add_to_queue, m)?)?;
    m.add_function(wrap_pyfunction!(get_next, m)?)?;
    m.add_function(wrap_pyfunction!(clear_queue, m)?)?;
    m.add_function(wrap_pyfunction!(queue_length, m)?)?;
    Ok(())
}

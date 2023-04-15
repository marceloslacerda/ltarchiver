
use pyo3::prelude::*;
use std::fs;
use std::io::BufReader;
use std::io::BufWriter;
use std::io::prelude::*;


use reed_solomon_erasure::galois_8::ReedSolomon;


/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pyfunction]
fn encode_file(source_file_path: String, destination_file_path: String, ecc_file_path: String, chunk_size: usize){
    let r = ReedSolomon::new(16, 1).unwrap();
    println!("Starting the encoding");
    // todo figure out the closest power of ten for the ecc_length
    let mut shards: Vec<Vec<u8>> = vec![vec![0; chunk_size]; 17];
    let mut buffer = vec![0; chunk_size * 16];
    let source_file = fs::File::open(source_file_path).unwrap();
    let mut reader = BufReader::new(source_file);
    let destination_file = fs::File::create(destination_file_path).unwrap();
    let ecc_file = fs::File::create(ecc_file_path).unwrap();
    let mut dest_stream = BufWriter::new(destination_file);
    let mut ecc_stream = BufWriter::new(ecc_file);
    while let Ok(size) = reader.read(&mut buffer) {
        if size == 0 {
            break;
        } else {
            ((size)..chunk_size).for_each(|i| {buffer[i] = 0});
            buffer.chunks(chunk_size).zip(0..16).for_each(|tup| {shards[tup.1].copy_from_slice(tup.0)});
            dest_stream.write(&buffer[0..size]).unwrap();
            r.encode(&mut shards).unwrap();
            ecc_stream.write(&shards[16]).unwrap();
        }
    }
    dest_stream.flush().unwrap();
    println!("Done");
}

/// A Python module implemented in Rust.
#[pymodule]
fn rust_module(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(encode_file, m)?)?;
    Ok(())
}

use pyo3::prelude::*;
use std::fs;
use std::io::BufReader;
use std::io::BufWriter;
use std::io::prelude::*;


use reed_solomon::Encoder;
use reed_solomon::Decoder;


/// Formats the sum of two numbers as string.
#[pyfunction]
fn sum_as_string(a: usize, b: usize) -> PyResult<String> {
    Ok((a + b).to_string())
}

#[pyfunction]
fn encode_file(
    source_file_path: String,
    destination_file_path: String,
    ecc_file_path: String,
    chunk_size: usize,
    ecc_len: usize
){
    let enc = Encoder::new(ecc_len);
    println!("Starting the encoding");
    let mut buffer = vec![0; chunk_size];
    let mut reader = BufReader::new(fs::File::open(source_file_path).unwrap());
    let mut dest_stream = BufWriter::new(fs::File::create(destination_file_path).unwrap());
    let mut ecc_stream = BufWriter::new(fs::File::create(ecc_file_path).unwrap());
    while let Ok(size) = reader.read(&mut buffer) {
        if size == 0 {
            break;
        } else {
            let encoded = enc.encode(&buffer[..]);
            ecc_stream.write(&encoded.ecc()).unwrap();
            dest_stream.write(&buffer[..]).unwrap();
        }
    }
    dest_stream.flush().unwrap();
    ecc_stream.flush().unwrap();
    println!("Done");
}

#[pyfunction]
fn decode_file(
    backup_file_path: String,
    destination_file_path: String,
    new_ecc_file_path: String,
    ecc_file_path: String,
    chunk_size: usize,
    ecc_len: usize
){
    let dec = Decoder::new(ecc_len);
    let mut backup_buffer = vec![0; chunk_size];
    let mut ecc_buffer = vec![0; ecc_len];
    let mut whole_buffer: Vec<u8> = vec![0; chunk_size + ecc_len];
    let mut reader = BufReader::new(fs::File::open(backup_file_path).unwrap());
    let mut ecc_stream = BufReader::new(fs::File::open(ecc_file_path).unwrap());
    let mut dest_stream = BufWriter::new(fs::File::create(destination_file_path).unwrap());
    let mut new_ecc_stream = BufWriter::new(fs::File::create(new_ecc_file_path).unwrap());
    println!("Starting the recovering process");
    loop {
        match reader.read(&mut backup_buffer) {
            Ok(size) => {
                if size == 0 {
                    break;
                } else {
                    match ecc_stream.read(&mut ecc_buffer) {
                        Ok(ecc_size) =>  {
                            if ecc_size == 0 {
                                eprintln!("ECC file was smaller than expected. Aborting");
                                break;
                            } else {
                                whole_buffer[0..size].copy_from_slice(&mut backup_buffer[0..size]);
                                whole_buffer[size..(size+ecc_len)].copy_from_slice(&mut ecc_buffer);
                                match dec.correct(&mut whole_buffer, None) {
                                    Ok(recovered) => {
                                        dest_stream.write(recovered.data()).unwrap();
                                        new_ecc_stream.write(recovered.ecc()).unwrap();
                                    }
                                    Err(err) => {
                                        eprint!("Could not correct the file due to an error {:?}", err);
                                        break;
                                    }
                                }
                                
                            }
                        }
                        Err(err) => {
                            eprintln!("Encountered an error while processing the ECC file: {err}");
                            break;
                        }
                    }
                }
            }
            Err(err) => {
                eprintln!("Encountered an error while processing the backup file: {err}");
                break;
            }
        }
    }
    dest_stream.flush().unwrap();
    new_ecc_stream.flush().unwrap();
    println!("Done");
}


/// A Python module implemented in Rust.
#[pymodule]
fn rust_module(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(sum_as_string, m)?)?;
    m.add_function(wrap_pyfunction!(encode_file, m)?)?;
    m.add_function(wrap_pyfunction!(decode_file, m)?)?;
    Ok(())
}
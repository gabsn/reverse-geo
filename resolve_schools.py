#!/usr/bin/env python3

import json
import reverse_geocoder as rg
import os
import argparse
import re
import multiprocessing
from tqdm import tqdm
import time
import sys
import threading

# Global lock for reverse_geocoder to prevent multiple processes from using it simultaneously
geocoder_lock = threading.Lock()

def process_coordinates(coordinates_batch):
    """Process a batch of coordinates using reverse_geocoder"""
    try:
        # Use a lock to prevent multiple processes from using reverse_geocoder simultaneously
        with geocoder_lock:
            return rg.search(coordinates_batch, mode=1)  # Mode 1 is more reliable
    except Exception as e:
        print(f"Error in reverse geocoding: {str(e)}")
        # Return empty results in case of error
        return [{'name': '', 'admin1': '', 'admin2': '', 'cc': ''} for _ in range(len(coordinates_batch))]

def process_batch(coordinates_batch, id_batch):
    """Process a batch of coordinates at once for better performance"""
    # Reverse geocode the batch of coordinates
    results_batch = process_coordinates(coordinates_batch)
    
    # Create a dictionary of results
    batch_results = {}
    for i, address_info in enumerate(results_batch):
        school_id = id_batch[i]
        batch_results[school_id] = {
            "address": {
                "name": address_info.get('name', ''),
                "admin1": address_info.get('admin1', ''),
                "admin2": address_info.get('admin2', ''),
                "cc": address_info.get('cc', '')
            }
        }
    
    return batch_results

def extract_school_data(school_text):
    """Extract school data from text using regex instead of JSON parsing"""
    school = {}
    
    # Extract name
    name_match = re.search(r'"name"\s*:\s*"([^"]*)"', school_text)
    if name_match:
        school['name'] = name_match.group(1)
    
    # Extract latitude
    lat_match = re.search(r'"latitude"\s*:\s*([-+]?\d*\.\d+|\d+)', school_text)
    if lat_match:
        school['latitude'] = float(lat_match.group(1))
    
    # Extract longitude
    lon_match = re.search(r'"longitude"\s*:\s*([-+]?\d*\.\d+|\d+)', school_text)
    if lon_match:
        school['longitude'] = float(lon_match.group(1))
    
    # Extract OSM ID
    osm_id_match = re.search(r'"id"\s*:\s*(\d+)', school_text)
    if osm_id_match:
        school['osm'] = {'id': int(osm_id_match.group(1))}
    
    return school

def process_chunk(chunk_data, batch_size=100):
    """Process a chunk of school data"""
    results = {}
    coordinates_batch = []
    id_batch = []
    schools_processed = 0
    
    for school_data in chunk_data:
        try:
            # Parse the school object using regex
            school = extract_school_data(school_data)
            
            # Extract school information
            school_id = str(school.get('osm', {}).get('id', ''))
            latitude = school.get('latitude')
            longitude = school.get('longitude')
            
            if school_id and latitude is not None and longitude is not None:
                # Add to batch
                coordinates_batch.append((latitude, longitude))
                id_batch.append(school_id)
                
                # Store additional info in results
                results[school_id] = {
                    "name": school.get('name', ''),
                    "coordinates": {
                        "latitude": latitude,
                        "longitude": longitude
                    }
                }
                
                # Process batch if it reaches the batch size
                if len(coordinates_batch) >= batch_size:
                    try:
                        batch_results = process_batch(coordinates_batch, id_batch)
                        
                        # Update results with address info
                        for school_id, address_data in batch_results.items():
                            if school_id in results:
                                results[school_id].update(address_data)
                        
                    except Exception as e:
                        print(f"\nError processing batch: {str(e)}")
                    
                    # Clear batches
                    coordinates_batch = []
                    id_batch = []
                    schools_processed += batch_size
        
        except Exception as e:
            print(f"\nError processing school data: {str(e)}")
    
    # Process any remaining items in the batch
    if coordinates_batch:
        try:
            batch_results = process_batch(coordinates_batch, id_batch)
            
            # Update results with address info
            for school_id, address_data in batch_results.items():
                if school_id in results:
                    results[school_id].update(address_data)
            
        except Exception as e:
            print(f"\nError processing final batch: {str(e)}")
    
    return results

def read_school_objects(input_file, max_schools=None):
    """Read school objects from the input file"""
    school_objects = []
    try:
        with open(input_file, 'r') as f:
            # Skip the opening bracket
            f.readline()
            
            # Read the file line by line
            line = f.readline()
            in_object = False
            current_object = ""
            count = 0
            
            while line:
                if line.strip() == '{':
                    in_object = True
                    current_object = '{'
                elif in_object and (line.strip() == '},' or line.strip() == '}'):
                    current_object += line
                    school_objects.append(current_object)
                    in_object = False
                    current_object = ""
                    count += 1
                    if max_schools and count >= max_schools:
                        break
                elif in_object:
                    current_object += line
                
                line = f.readline()
    except Exception as e:
        print(f"Error reading file: {str(e)}")
    
    return school_objects

def save_results(results, output_file):
    """Save results to the output file with error handling"""
    try:
        temp_file = f"{output_file}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(results, f)
        
        # Rename temp file to final file to ensure atomic write
        os.replace(temp_file, output_file)
        return True
    except Exception as e:
        print(f"Error saving results: {str(e)}")
        return False

def process_schools_sequentially(school_objects, batch_size, output_file, existing_results=None):
    """Process schools sequentially without multiprocessing"""
    results = existing_results or {}
    total_schools = len(school_objects)
    
    # Process in smaller batches
    coordinates_batch = []
    id_batch = []
    last_save_time = time.time()
    save_interval = 60  # Save every 60 seconds
    
    for i, school_data in enumerate(tqdm(school_objects, desc="Processing schools")):
        try:
            # Parse the school object using regex
            school = extract_school_data(school_data)
            
            # Extract school information
            school_id = str(school.get('osm', {}).get('id', ''))
            latitude = school.get('latitude')
            longitude = school.get('longitude')
            
            if school_id and latitude is not None and longitude is not None:
                # Add to batch
                coordinates_batch.append((latitude, longitude))
                id_batch.append(school_id)
                
                # Store additional info in results
                results[school_id] = {
                    "name": school.get('name', ''),
                    "coordinates": {
                        "latitude": latitude,
                        "longitude": longitude
                    }
                }
                
                # Process batch if it reaches the batch size
                if len(coordinates_batch) >= batch_size:
                    try:
                        batch_results = process_batch(coordinates_batch, id_batch)
                        
                        # Update results with address info
                        for school_id, address_data in batch_results.items():
                            if school_id in results:
                                results[school_id].update(address_data)
                        
                    except Exception as e:
                        print(f"\nError processing batch: {str(e)}")
                    
                    # Clear batches
                    coordinates_batch = []
                    id_batch = []
                    
                    # Save results periodically
                    current_time = time.time()
                    if current_time - last_save_time > save_interval:
                        print(f"\nSaving results after processing {i+1}/{total_schools} schools...")
                        if save_results(results, output_file):
                            last_save_time = current_time
                        print(f"Total schools processed so far: {len(results)}")
        
        except Exception as e:
            print(f"\nError processing school data: {str(e)}")
    
    # Process any remaining items in the batch
    if coordinates_batch:
        try:
            batch_results = process_batch(coordinates_batch, id_batch)
            
            # Update results with address info
            for school_id, address_data in batch_results.items():
                if school_id in results:
                    results[school_id].update(address_data)
            
        except Exception as e:
            print(f"\nError processing final batch: {str(e)}")
    
    return results

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Resolve school addresses using reverse geocoder')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size for processing (default: 100)')
    parser.add_argument('--input-file', default='data/schools.json', help='Input JSON file (default: data/schools.json)')
    parser.add_argument('--output-file', default='school_addresses.json', help='Output JSON file (default: school_addresses.json)')
    parser.add_argument('--num-processes', type=int, default=1, help='Number of processes to use (default: 1)')
    parser.add_argument('--chunk-size', type=int, default=5000, help='Number of schools to process in each chunk (default: 5000)')
    parser.add_argument('--max-schools', type=int, default=None, help='Maximum number of schools to process (default: all)')
    parser.add_argument('--save-interval', type=int, default=60, help='Save interval in seconds (default: 60)')
    parser.add_argument('--sequential', action='store_true', help='Process schools sequentially without multiprocessing')
    args = parser.parse_args()
    
    # Output file
    output_file = args.output_file
    
    # Check if output file exists and load existing results
    results = {}
    if os.path.exists(output_file):
        print(f"Loading existing results from {output_file}")
        try:
            with open(output_file, 'r') as f:
                results = json.load(f)
            print(f"Loaded {len(results)} existing results")
        except json.JSONDecodeError:
            print(f"Error loading existing results, starting fresh")
    
    print(f"Processing schools from {args.input_file} with batch size {args.batch_size}...")
    
    # Read the file and extract school objects
    print("Reading school objects from file...")
    school_objects = read_school_objects(args.input_file, args.max_schools)
    print(f"Extracted {len(school_objects)} school objects")
    
    # Filter out schools that are already processed
    if results:
        filtered_objects = []
        print("Filtering already processed schools...")
        for obj in tqdm(school_objects):
            school = extract_school_data(obj)
            school_id = str(school.get('osm', {}).get('id', ''))
            if school_id and school_id not in results:
                filtered_objects.append(obj)
        
        print(f"Filtered to {len(filtered_objects)} unprocessed schools")
        school_objects = filtered_objects
    
    if not school_objects:
        print("No schools to process. Exiting.")
        sys.exit(0)
    
    start_time = time.time()
    
    # Process schools
    if args.sequential or args.num_processes == 1:
        # Process sequentially
        print("Processing schools sequentially...")
        results = process_schools_sequentially(school_objects, args.batch_size, output_file, results)
    else:
        # Process in chunks with multiprocessing
        total_chunks = (len(school_objects) + args.chunk_size - 1) // args.chunk_size
        print(f"Processing in {total_chunks} chunks with {args.num_processes} processes")
        
        # Create a multiprocessing context that uses 'spawn' method
        ctx = multiprocessing.get_context('spawn')
        
        # Set up multiprocessing with non-daemon processes
        pool = ctx.Pool(processes=args.num_processes)
        
        # Process each chunk
        last_save_time = start_time
        
        try:
            for chunk_idx in range(total_chunks):
                start_idx = chunk_idx * args.chunk_size
                end_idx = min(start_idx + args.chunk_size, len(school_objects))
                chunk = school_objects[start_idx:end_idx]
                
                print(f"Processing chunk {chunk_idx+1}/{total_chunks} with {len(chunk)} schools")
                
                # Split the chunk into smaller parts for multiprocessing
                chunk_parts = []
                part_size = (len(chunk) + args.num_processes - 1) // args.num_processes
                for i in range(0, len(chunk), part_size):
                    chunk_parts.append(chunk[i:i+part_size])
                
                # Process each part in parallel
                part_results = pool.map(
                    process_chunk, 
                    [(part, args.batch_size) for part in chunk_parts]
                )
                
                # Merge results from all parts
                for part_result in part_results:
                    results.update(part_result)
                
                # Save results periodically
                current_time = time.time()
                if current_time - last_save_time > args.save_interval:
                    print(f"Saving results after chunk {chunk_idx+1}...")
                    if save_results(results, output_file):
                        last_save_time = current_time
                    
                print(f"Total schools processed so far: {len(results)}")
        
        finally:
            # Close the pool
            pool.close()
            pool.join()
    
    # Save final results
    print("Saving final results...")
    save_results(results, output_file)
    
    # Print summary
    elapsed_time = time.time() - start_time
    print(f"Done! Processed {len(results)} schools in {elapsed_time:.2f} seconds.")
    print(f"Results saved to {output_file}")

if __name__ == "__main__":
    main() 
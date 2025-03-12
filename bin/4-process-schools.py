#!/usr/bin/env python3

import json
import os
import sys
import time
from tqdm import tqdm
import argparse
import multiprocessing
from functools import partial
import queue

# Import the reverse geocoding function from the existing script
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from reverse_geocoding import get_administrative_boundaries

def process_school(school, debug=False):
    """
    Process a single school and return the result.
    
    Args:
        school: School data dictionary
        debug: Whether to enable debug output
    
    Returns:
        Tuple of (osm_id, result_dict)
    """
    # Extract required information
    name = school.get('name', 'Unknown')
    lat = school.get('latitude')
    lon = school.get('longitude')
    osm_data = school.get('osm', {})
    osm_id = f"{osm_data.get('type', 'N')[0].upper()}{osm_data.get('id', 0)}"
    
    # Skip if missing coordinates
    if lat is None or lon is None:
        if debug:
            print(f"Skipping school '{name}' due to missing coordinates")
        return None
    
    # Get address information using reverse geocoding
    try:
        address_json = get_administrative_boundaries(lat, lon, debug)
        address = json.loads(address_json)
        
        # Create result dictionary
        result = {
            "name": name,
            "address": {
                "countryCode": address.get("countryCode"),
                "country": address.get("country"),
                "state": address.get("state"),
                "city": address.get("city")
            }
        }
        
        return (osm_id, result)
            
    except Exception as e:
        if debug:
            print(f"Error processing school '{name}': {str(e)}")
        
        # Return with error information
        return (osm_id, {
            "name": name,
            "error": str(e),
            "address": {
                "countryCode": None,
                "country": None,
                "state": None,
                "city": None
            }
        })

def result_collector(result_queue, output_file, total_to_process, debug=False, save_interval=100):
    """
    Collect results from worker processes and save them periodically.
    
    Args:
        result_queue: Queue to receive results from workers
        output_file: Path to the output JSON file
        total_to_process: Total number of schools being processed
        debug: Whether to enable debug output
        save_interval: Number of schools to process before saving progress
    """
    # Initialize result dictionary
    result = {}
    
    # Check if output file exists and load existing results
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                result = json.load(f)
            if debug:
                print(f"Collector: Loaded {len(result)} already processed schools from {output_file}.")
        except Exception as e:
            if debug:
                print(f"Collector: Error loading existing results: {e}")
                print("Collector: Starting with an empty result set.")
    
    # Variables for tracking progress and saving
    processed_count = 0
    error_count = 0
    last_save_time = time.time()
    
    # Create progress bar
    pbar = tqdm(total=total_to_process, desc="Processing schools")
    
    try:
        while processed_count < total_to_process:
            try:
                # Get result with timeout to allow for keyboard interrupts
                item = result_queue.get(timeout=1)
                
                if item is None:
                    # Skip None results (schools with missing coordinates)
                    continue
                
                osm_id, school_result = item
                
                # Add to result dictionary
                result[osm_id] = school_result
                
                # Check if there was an error
                if "error" in school_result:
                    error_count += 1
                
                processed_count += 1
                pbar.update(1)
                
                # Save progress periodically
                if (processed_count % save_interval == 0 or 
                    time.time() - last_save_time > 60):  # Save every minute or every save_interval schools
                    save_results(result, output_file, debug)
                    last_save_time = time.time()
                    
            except queue.Empty:
                # No results available, just continue
                continue
    except KeyboardInterrupt:
        print("\nCollector: Interrupted by user. Saving current progress...")
    finally:
        # Final save
        if processed_count > 0:
            save_results(result, output_file, debug)
            print(f"\nSuccessfully processed {processed_count} schools.")
            if error_count > 0:
                print(f"Encountered errors with {error_count} schools.")
        
        pbar.close()

def process_schools(input_file, output_file, debug=False, save_interval=100, num_workers=None):
    """
    Process schools data from input_file, add address information using reverse geocoding,
    and save the results to output_file using multiple processes.
    
    Args:
        input_file: Path to the input JSON file containing schools data
        output_file: Path to the output JSON file for saving results
        debug: Whether to enable debug output
        save_interval: Number of schools to process before saving progress
        num_workers: Number of worker processes to use (defaults to CPU count)
    """
    # Determine number of workers
    if num_workers is None:
        num_workers = max(1, multiprocessing.cpu_count() - 1)  # Leave one CPU for the main process
    
    print(f"Using {num_workers} worker processes")
    
    # Load schools data
    print(f"Loading schools data from {input_file}...")
    try:
        with open(input_file, 'r') as f:
            schools = json.load(f)
    except Exception as e:
        print(f"Error loading schools data: {e}")
        sys.exit(1)
    
    print(f"Loaded {len(schools)} schools.")
    
    # Check if output file exists and load existing results to determine which schools to process
    processed_ids = set()
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r') as f:
                result = json.load(f)
            processed_ids = set(result.keys())
            print(f"Loaded {len(processed_ids)} already processed schools from {output_file}.")
        except Exception as e:
            print(f"Error loading existing results: {e}")
            print("Starting with an empty result set.")
    
    # Filter schools that need processing
    schools_to_process = []
    for school in schools:
        osm_data = school.get('osm', {})
        osm_id = f"{osm_data.get('type', 'N')[0].upper()}{osm_data.get('id', 0)}"
        
        # Only add schools that haven't been processed yet
        if osm_id not in processed_ids:
            schools_to_process.append(school)
    
    if not schools_to_process:
        print("All schools have already been processed. Nothing to do.")
        return
    
    print(f"Processing {len(schools_to_process)} schools out of {len(schools)} total...")
    
    # Create a queue for results
    result_queue = multiprocessing.Queue()
    
    # Start the result collector process
    collector_process = multiprocessing.Process(
        target=result_collector,
        args=(result_queue, output_file, len(schools_to_process), debug, save_interval)
    )
    # Set daemon to False to avoid the "daemonic processes are not allowed to have children" error
    collector_process.daemon = False
    collector_process.start()
    
    # Create a pool of worker processes
    try:
        # Process schools in chunks to avoid creating too many processes
        chunk_size = 100  # Process 100 schools at a time
        for i in range(0, len(schools_to_process), chunk_size):
            chunk = schools_to_process[i:i+chunk_size]
            
            # Process this chunk with a fresh pool
            with multiprocessing.Pool(num_workers) as pool:
                # Process schools in parallel
                process_func = partial(process_school, debug=debug)
                for result in pool.imap_unordered(process_func, chunk):
                    if result is not None:
                        result_queue.put(result)
    except KeyboardInterrupt:
        print("\nInterrupted by user. Waiting for workers to finish...")
    finally:
        # Signal that no more results will be coming
        result_queue.put(None)
        
        # Wait for the collector to finish
        collector_process.join()

def save_results(result, output_file, debug=False):
    """Save the current results to the output file."""
    if debug:
        print(f"Saving progress to {output_file}...")
    
    # Create a temporary file to avoid data loss if the script is interrupted during saving
    temp_file = f"{output_file}.tmp"
    try:
        with open(temp_file, 'w') as f:
            json.dump(result, f, indent=2)
        
        # Rename the temporary file to the actual output file
        os.replace(temp_file, output_file)
        
        if debug:
            print(f"Successfully saved {len(result)} schools with address information.")
    except Exception as e:
        print(f"Error saving results: {e}")
        # Don't exit, just continue processing

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process schools data and add address information')
    parser.add_argument('--input', default='data/schools.json', help='Input JSON file containing schools data')
    parser.add_argument('--output', default='data/schools-with-addresses.json', help='Output JSON file for schools with addresses')
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--save-interval', type=int, default=100, help='Number of schools to process before saving progress')
    parser.add_argument('--workers', type=int, default=None, help='Number of worker processes to use (defaults to CPU count)')
    
    args = parser.parse_args()
    
    process_schools(args.input, args.output, args.debug, args.save_interval, args.workers) 
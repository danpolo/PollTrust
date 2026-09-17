from polltrust.metrics import balanced_benchmark, leave_one_election_out_debiased_errors, seat_transfer_distance

def test_seat_transfer_distance_counts_transfers_once():
    assert seat_transfer_distance({"a":40,"b":30,"c":50},{"a":35,"b":35,"c":50})==5

def test_balanced_benchmark_weights_clusters_not_pollster_count():
    predictions=[("p1",{"a":70,"b":50}),("p2",{"a":70,"b":50}),("p3",{"a":50,"b":70})]
    assert balanced_benchmark(predictions,{"p1":"x","p2":"x","p3":"y"})=={"a":60,"b":60}

def test_leave_one_out_does_not_use_target_election_bias():
    records=[{"predicted":{"a":65,"b":55},"actual":{"a":60,"b":60}},{"predicted":{"a":65,"b":55},"actual":{"a":60,"b":60}},{"predicted":{"a":50,"b":70},"actual":{"a":60,"b":60}}]
    corrected=leave_one_election_out_debiased_errors(records)
    assert len(corrected)==3 and corrected[0]!=0

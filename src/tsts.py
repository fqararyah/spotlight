import space

num_levels = 2
pe_low = 128
pe_high = 256
pe_step = 1
    
pe_range = range(pe_low, pe_high+1, pe_step)

for num_pe in pe_range:
    print(space.get_all_combinations_v2(num_levels, num_pe, [], []))

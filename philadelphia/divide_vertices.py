import sys
import time
from pysat.solvers import Solver
from pysat.card import CardEnc


def read_dataset(file_path):
    num_cells = 0
    demand_vector = [0]  # Thêm 0 ở đầu để index bắt đầu từ 1
    matrix = []
    
    with open(file_path, 'r') as file:
        # Đọc tất cả các dòng, loại bỏ khoảng trắng dư thừa và dòng trống
        lines = [line.strip() for line in file if line.strip()]
        
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Đọc số lượng cells
        if line.startswith("Number of cells:"):
            num_cells = int(line.split(":")[1].strip())
            
            # Khởi tạo ma trận với dòng index 0 rỗng (toàn số 0)
            matrix.append([0] * (num_cells + 1))
            
        # Đọc Demand Vector
        elif line.startswith("Demand Vector:"):
            i += 1  # Chuyển sang dòng chứa dữ liệu
            demands = list(map(int, lines[i].split(',')))
            demand_vector.extend(demands)
            
        # Đọc Matrix
        elif line.startswith("Matrix for"):
            i += 1  # Chuyển sang dòng chứa dòng đầu tiên của ma trận
            for _ in range(num_cells):
                if i < len(lines):
                    row_data = list(map(int, lines[i].split(',')))
                    # Thêm 0 ở đầu mỗi dòng để cột cũng có index bắt đầu từ 1
                    matrix.append([0] + row_data)
                    i += 1
            break  # Hoàn thành đọc ma trận
            
        i += 1

    return num_cells, demand_vector, matrix


def create_frequency_var(num_cells, demand_vector, num_frequencies):

    x = [None] * (num_cells + 1)
    top = 0

    for i in range(1, num_cells + 1):
        demands = demand_vector[i]
        cell_vars = [[0] * (num_frequencies + 1) for _ in range(demands + 1)]
        
        for k in range(1, demands + 1):
            for j in range(1, num_frequencies + 1):
                top += 1
                cell_vars[k][j] = top
                
        x[i] = cell_vars

    return x, top


def create_order_var(solver, num_cells, demand_vector, num_frequencies, top, x):
    g = [None] * (num_cells + 1)
    # Khởi tạo biến g
    for i in range(1, num_cells + 1):
        demands = demand_vector[i]
        cell_vars = [[0] * (num_frequencies + 1) for _ in range(demands + 1)]
        
        for k in range(1, demands + 1):
            for j in range(1, num_frequencies + 1):
                top += 1
                cell_vars[k][j] = top
                
        g[i] = cell_vars
    
    for i in range(1, num_cells + 1):
        demands = demand_vector[i]
        for l in range(1, demands + 1):
            solver.add_clause([g[i][l][1]])  # (2) g[i][l][1]
            for j in range(2, num_frequencies + 1):
                solver.add_clause([-g[i][l][j], g[i][l][j-1]])  # (3) g[i][l][j] => g[i][l][j-1]
            #  xi,l,j ↔ gi,j,l ∧ ¬gi,l,j+1 
            for j in range(1, num_frequencies):
                solver.add_clause([-x[i][l][j], g[i][l][j]])  
                solver.add_clause([-x[i][l][j], -g[i][l][j+1]])  
                solver.add_clause([-g[i][l][j], g[i][l][j+1], x[i][l][j]])  
            # xi,l,num_frequencies ↔ gi,l,num_frequencies
            solver.add_clause([-x[i][l][num_frequencies], g[i][l][num_frequencies]])
            solver.add_clause([-g[i][l][num_frequencies], x[i][l][num_frequencies]])
              
    return g, top            

    

def add_distance_constraints(solver, num_cells, num_frequencies, x, g, demand_vector, matrix):
    # Ràng buộc khoảng cách Co-site
    for i in range(1, num_cells + 1):
        for l1 in range(1, demand_vector[i] + 1):
            for l2 in range(l1 + 1, demand_vector[i] + 1):
                d = matrix[i][i]
                for j in range(1, num_frequencies + 1):
                    # ép thứ tự tần số được nhận từ nhỏ đến lớn
                    if j + d <= num_frequencies:
                        solver.add_clause([-x[i][l1][j], g[i][l2][j + d]])
                    else:
                        solver.add_clause([-x[i][l1][j]])

    # Ràng buộc khoảng cách Inter-site
    for u in range(1, num_cells + 1):
        for v in range(u + 1, num_cells + 1):
            d = matrix[u][v]
            if d > 0:
                for l1 in range(1, demand_vector[u] + 1):
                    for l2 in range(1, demand_vector[v] + 1):
                        for j in range(1, num_frequencies + 1):
                            clause = [-x[u][l1][j]]
                            if j - d + 1 >= 1:
                                clause.append(-g[v][l2][j - d + 1])
                            if j + d <= num_frequencies:
                                clause.append(g[v][l2][j + d])
                            solver.add_clause(clause)

def create_frequency_constraints(solver, num_cells, num_frequencies, x, top):
    f = [0] * (num_frequencies + 1)
    for j in range(1, num_frequencies + 1):
        top += 1
        f[j] = top

    for i in range(1, num_cells + 1):
        for l in range(1, demand_vector[i] + 1):
            for j in range(1, num_frequencies + 1):
                solver.add_clause([-x[i][l][j], f[j]])  # Nếu x[i][l][j] = 1 thì f[j] = 1

    return f, top

    

def greedy(num_cells, demand, distance_matrix):
   
    assignment = {i: [] for i in range(1, num_cells + 1)}
    
    sorted_cells = sorted(range(1, num_cells + 1), key=lambda x: demand[x], reverse=True)
    
    for cell in sorted_cells:
        for _ in range(demand[cell]):
            freq = 1  # Tần số bắt đầu thử vẫn là 1
            
            while True:
                has_conflict = False
                
                # Kiểm tra nhiễu Co-site (d_ii)
                co_site_dist = distance_matrix[cell][cell]
                for used_f in assignment[cell]:
                    if abs(freq - used_f) < co_site_dist:
                        has_conflict = True
                        break
                
                # Kiểm tra nhiễu Inter-site (d_ij)
                if not has_conflict:
                    # Vòng lặp các trạm lân cận cũng chạy từ 1 đến num_cells
                    for other_cell in range(1, num_cells + 1):
                        if other_cell == cell or not assignment[other_cell]:
                            continue
                        
                        inter_site_dist = distance_matrix[cell][other_cell]
                        if inter_site_dist > 0:
                            for used_f in assignment[other_cell]:
                                if abs(freq - used_f) < inter_site_dist:
                                    has_conflict = True
                                    break
                        
                        if has_conflict:
                            break
                
                # Tăng tần số nếu có xung đột, ngược lại chốt gán
                if has_conflict:
                    freq += 1
                else:
                    assignment[cell].append(freq)
                    break
                    
    # Tìm Max Freq (num_frequencies) an toàn, tránh lỗi nếu đồ thị rỗng
    max_freq = 0
    for freqs in assignment.values():
        if freqs:
            max_freq = max(max_freq, max(freqs))
            
    return max_freq, assignment

def solve_and_print(solver, num_cells, num_frequencies, x, demand_vector, matrix):
    span = None
    assignment = None
    if solver.solve():
        model = solver.get_model()
        assignment = {i: [] for i in range(1, num_cells + 1)}
        
        for i in range(1, num_cells + 1):
            for l in range(1, demand_vector[i] + 1):
                for j in range(1, num_frequencies + 1):
                    var = x[i][l][j]
                    if var in model:
                        assignment[i].append(j)
                        break
        
        max_freq = 0
        min_freq = float('inf')
        for freqs in assignment.values():
            if freqs:
                max_freq = max(max_freq, max(freqs))
                min_freq = min(min_freq, min(freqs))
        span = max_freq - min_freq
        print(f"Found solution with span: {span} ({max_freq} - {min_freq})")
    else:
        print("No solution found.")
    return span, assignment

def verify_solution(assignment, demand_vector, distance_matrix):
    for cell, freqs in assignment.items():
        if len(freqs) != demand_vector[cell]:
            return False
        # Kiểm tra nhiễu Co-site
        for i in range(len(freqs)):
            for j in range(i + 1, len(freqs)):
                if abs(freqs[i] - freqs[j]) < distance_matrix[cell][cell]:
                    return False
        
        # Kiểm tra nhiễu Inter-site
        for other_cell, other_freqs in assignment.items():
            if other_cell == cell:
                continue
            
            inter_site_dist = distance_matrix[cell][other_cell]
            if inter_site_dist > 0:
                for f1 in freqs:
                    for f2 in other_freqs:
                        if abs(f1 - f2) < inter_site_dist:
                            return False
    return True
if __name__ == "__main__":
    start_time = time.perf_counter()

    dataset = sys.argv[1]
    file_path = f"dataset/{dataset}.txt"

    num_cells, demand_vector, matrix = read_dataset(file_path)
    max_frequency, greedy_assignment = greedy(num_cells, demand_vector, matrix)
    UB = max_frequency - 1  # Bắt đầu với num_frequencies = max_frequency

    print(f"Greedy span: {UB} (max_frequency: {max_frequency})")
    if verify_solution(greedy_assignment, demand_vector, matrix):
        print("Greedy solution is valid.")
    else:
        print("Greedy solution is invalid.")

    num_frequencies = UB   # Giảm num_frequencies để bắt đầu tìm kiếm giải pháp tốt hơn
    UB = num_frequencies  # Upper bound ban đầu là span từ giải pháp greedy
    solver = Solver(name='cadical195')

    x, top = create_frequency_var(num_cells,demand_vector, num_frequencies)
    g, top = create_order_var(solver, num_cells, demand_vector, num_frequencies, top, x)
    add_distance_constraints(solver, num_cells, num_frequencies, x, g, demand_vector, matrix)
    f, top = create_frequency_constraints(solver, num_cells, num_frequencies, x, top)


    # solver.add_clause([f[1]])
    while True:
        print("--------------------------------")
        print(f"Trying with num_frequencies = {UB}...")
        span, assignment = solve_and_print(solver, num_cells, num_frequencies, x, demand_vector, matrix)
        if assignment:
            print(f"Time taken: {time.perf_counter() - start_time:.2f}s")

            for i in range(span + 1, UB + 1):
                solver.add_clause([-f[i]])  # Ràng buộc mới: f[i] = 0 cho i >= span
            UB = span  # Cập nhật num_frequencies mới dựa trên span tìm được
        else:
            print(f"Optimal span found: {num_frequencies}")
            print(f"Time taken: {time.perf_counter() - start_time:.2f}s")
            break
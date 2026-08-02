// 四状态 FSM：IDLE -> LOAD -> RUN -> DONE -> IDLE
// 功能：等待 start，装载 8 位数据，运行 4 个时钟周期，然后输出 done
//
// 输入：clk, rst_n（低有效异步复位）, start, data_in[7:0]
// 输出：done, data_out[7:0], state[1:0]（调试用）

module fsm4 (
    input  wire       clk,
    input  wire       rst_n,
    input  wire       start,
    input  wire [7:0] data_in,
    output reg        done,
    output reg  [7:0] data_out,
    output reg  [1:0] state
);

    localparam IDLE = 2'b00;
    localparam LOAD = 2'b01;
    localparam RUN  = 2'b10;
    localparam DONE = 2'b11;

    reg [1:0] nxt_state;
    reg [1:0] run_cnt;

    // 1) 状态寄存器（时序逻辑）：每个时钟沿把 nxt_state 锁存为当前状态
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            state <= IDLE;
        else
            state <= nxt_state;
    end

    // 2) next-state 组合逻辑：根据当前状态和输入决定下一个状态
    always @(*) begin
        nxt_state = state;
        case (state)
            IDLE: if (start)            nxt_state = LOAD;
            LOAD:                       nxt_state = RUN;
            RUN:  if (run_cnt == 2'd4)  nxt_state = DONE;
            DONE:                       nxt_state = IDLE;
            default:                    nxt_state = IDLE;  // 非法状态恢复
        endcase
    end

    // 3) RUN 状态计数器：在 RUN 中计数 0..3
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            run_cnt <= 2'd0;
        else if (state == RUN)
            run_cnt <= run_cnt + 1'b1;
        else
            run_cnt <= 2'd0;
    end

    // 4) 数据寄存器：LOAD 周期装载输入数据，之后保持
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n)
            data_out <= 8'd0;
        else if (state == LOAD)
            data_out <= data_in;
    end

    // 5) 输出逻辑（Moore 型）：只取决于当前状态
    always @(*) begin
        done = 1'b0;
        if (state == DONE)
            done = 1'b1;
    end

endmodule

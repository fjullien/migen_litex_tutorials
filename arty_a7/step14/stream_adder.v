module stream_adder (
    input  wire sink_valid,
    input  wire sink_last,
    input  wire [7:0] sink_data,
    output wire sink_ready,

    output wire source_valid,
    output wire source_last,
    output wire [7:0] source_data,
    input  wire source_ready
);

assign source_valid = sink_valid;
assign source_last = sink_last;
assign source_data = sink_data + 1;
assign sink_ready = source_ready;

endmodule

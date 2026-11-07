package com.psi.training.nexacro.xapi.entity.response;


import lombok.Data;

import java.util.List;

@Data
public class ResponseEntity {

    private int code;
    private String message;
    private List<Dataset> datasets;

    public ResponseEntity(int code, String message, List<Dataset> datasets) {
        this.code = code;
        this.message = message;
        this.datasets = datasets;
    }
}
